import redis, json, os
from configuration import REDIS_URL

r = redis.from_url(REDIS_URL)
MAX_HISTORY = 5

def set_user_context(user_id: str, data: dict):
    r.set(f"{user_id}:ctx", json.dumps(data))

def get_user_context(user_id: str) -> dict:
    raw = r.get(f"{user_id}:ctx")
    return json.loads(raw) if raw else {}

def clear_user_context(user_id: str):
    # delete both context & history & PDF file
    ctx = get_user_context(user_id)
    pdf = ctx.get("last_pdf_path")
    if pdf and os.path.exists(pdf):
        os.remove(pdf)
    r.delete(f"{user_id}:ctx")
    r.delete(f"{user_id}:history")

def append_user_history(user_id: str, question: str, answer: str):
    key = f"{user_id}:history"
    raw = r.get(key)
    hist = json.loads(raw) if raw else []
    hist.append({"role": "user", "content": question})
    hist.append({"role": "assistant", "content": answer})
    hist = hist[-(MAX_HISTORY * 2):]  # keep last N turns
    r.set(key, json.dumps(hist))

def get_user_history(user_id: str) -> list[dict]:
    raw = r.get(f"{user_id}:history")
    return json.loads(raw) if raw else []
