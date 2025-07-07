import re, os
from pywa import filters, types, WhatsApp
from pywa.types import CallbackButton
from ingestion import parse_pdf
from vectorstore import add_documents, query_vectorstore, summarize_user_documents
from memory import (
    set_user_context, get_user_context, clear_user_context,
    append_user_history, get_user_history
)
from llm import rewrite_query, ask_gemini_with_history

# Buttons
BUTTONS_START = [
    types.Button(title="📋 Summary", callback_data="SUMMARY"),
    types.Button(title="❓ Query",   callback_data="QUERY")
]
BUTTONS_CONTINUE = [
    types.Button(title="📋 Summary",      callback_data="SUMMARY"),
    types.Button(title="❓ Continue Q&A", callback_data="QUERY"),
    types.Button(title="🚪 End Session",  callback_data="END")
]

def normalize_history(raw_history):
    """
    Accepts a list of dicts from Redis, which may be either:
      - {"role":"user"/"assistant", "content": "..."}
      - {"q": "...", "a": "..."}
    Returns a flat list of {"role", "content"} entries.
    """
    out = []
    for turn in raw_history:
        if "role" in turn and "content" in turn:
            out.append({"role": turn["role"], "content": turn["content"]})
        elif "q" in turn and "a" in turn:
            out.append({"role": "user",      "content": turn["q"]})
            out.append({"role": "assistant", "content": turn["a"]})
        else:
            # skip malformed entries
            continue
    return out

def register(wa: WhatsApp):
    # Greeting
    @wa.on_message(filters.text & filters.regex(r"^(hi|hello|hey)$", flags=re.IGNORECASE))
    def on_greeting(_, msg: types.Message):
        msg.reply_text(
            "👋 Hello! I’m your PDF Q&A assistant. Please send me the PDF you want to talk about!",
        )

    # PDF upload
    @wa.on_message(filters.document)
    def on_pdf(_, msg: types.Message):
        user = msg.from_user.wa_id
        msg.reply_text("📑 Parsing PDF, please wait…")

        # 1) Download
        path = msg.document.download()

        # 2) Save context (including PDF path for cleanup)
        ctx = get_user_context(user) or {}
        ctx.update({
            "has_pdf": True,
            "query_count": 0,
            "last_pdf_path": path
        })
        set_user_context(user, ctx)

        # 3) Attempt parsing + indexing
        try:
            chunks = parse_pdf(path)
        except Exception as e:
            print("PDF parsing error:", e)
            return msg.reply_text(
                "❌ Sorry, I couldn’t parse that PDF right now. "
                "Please send it again."
            )

        try:
            add_documents(user, chunks)
        except Exception as e:
            print("Indexing error:", e)
            return msg.reply_text(
                "❌ PDF was parsed but indexing failed. "
                "Please send the PDF one more time."
            )

        # 4) Success
        msg.reply_text("✅ PDF indexed! What next?", buttons=BUTTONS_START)

    # Summary
    @wa.on_callback_button(filters.matches("SUMMARY"))
    def on_summary(_, cb: CallbackButton):
        user = cb.from_user.wa_id
        ctx = get_user_context(user) or {}
        raw_history = get_user_history(user)
        history = normalize_history(raw_history)


        # pick context to summarize
        if ctx.get("last_reply"):
            context = ctx["last_reply"]
        else:
            context = summarize_user_documents(user, lambda x: x)

        answer = ask_gemini_with_history(
            history, context,
            "Please summarize the above text in detail."
        )
        # split if too long
        MAX = 4000
        for i in range(0, len(answer), MAX):
            cb.reply_text(answer[i:i+MAX])
        append_user_history(user, "SUMMARY", answer)

    # Switch to query mode
    @wa.on_callback_button(filters.matches("QUERY"))
    def on_query_mode(_, cb: CallbackButton):
        user = cb.from_user.wa_id
        ctx = get_user_context(user) or {}
        ctx["mode"] = "querying"
        set_user_context(user, ctx)
        cb.reply_text("❓ Send me your question.")

    # End session
    @wa.on_callback_button(filters.matches("END"))
    def on_end(_, cb: CallbackButton):
        user = cb.from_user.wa_id
        clear_user_context(user)
        cb.reply_text("👋 Session ended. Send 'hi' to start a new one.")

    # Free-text query handler
    @wa.on_message(filters.text)
    def on_query(_, msg: types.Message):
        user = msg.from_user.wa_id
        ctx = get_user_context(user) or {}
        if not ctx.get("has_pdf"):
            return msg.reply_text("📄 Please send a PDF first!")

        question = msg.text.strip()
        # 1) rewrite
        terms = rewrite_query(question)

        # 2) retrieve
        docs, metas = query_vectorstore(user, top_k=15)
        # simple re-filter by terms presence
        paragraphs = []
        for d,m in zip(docs, metas):
            if any(t.lower() in d.lower() for t in terms):
                paragraphs.append(d)
        if not paragraphs:
            # fallback to all top-K
            paragraphs = docs[:5]

        # 3) prepare context
        context = "\n\n".join(paragraphs)
        raw_history = get_user_history(user)
        history = normalize_history(raw_history)


        # 4) ask LLM
        answer = ask_gemini_with_history(history, context, question)
        # reply (split if needed)
        MAX = 4000
        for i in range(0, len(answer), MAX):
            msg.reply_text(answer[i:i+MAX])

        # 5) update memory
        append_user_history(user, question, answer)
        count = ctx.get("query_count", 0) + 1
        ctx["query_count"] = count
        set_user_context(user, ctx)
        if count % 3 == 0:
            msg.reply_text("What next?", buttons=BUTTONS_CONTINUE)
