import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
embedding_function = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

client = chromadb.Client()
collection = client.get_or_create_collection(
    name="pdf_docs",
    embedding_function=embedding_function
)

def add_documents(user_id: str, chunks: list):
    # Remove old docs for this user
    collection.delete(where={"user_id": user_id})

    texts = []
    metadatas = []
    ids = []
    for i, c in enumerate(chunks):
        texts.append(c["page_content"])
        # drop None values and stringify
        clean_meta = {}
        for k, v in c["metadata"].items():
            if v is None:
                continue
            clean_meta[k] = str(v)
        clean_meta["user_id"] = user_id

        metadatas.append(clean_meta)
        ids.append(f"{user_id}_{i}")

    # Now add—will never pass None into metadata
    collection.add(documents=texts, metadatas=metadatas, ids=ids)

def query_vectorstore(user_id: str, top_k: int = 10):
    res = collection.query(
        query_texts=[ "" ],  # we overwrite this in handlers
        n_results=top_k,
        where={"user_id": user_id},
        include=["documents", "metadatas"]
    )
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    return docs, metas

def summarize_user_documents(user_id: str, model_fn) -> str:
    pages = collection.get(where={"user_id": user_id}).get("documents", [])
    # flatten list of lists
    all_text = "\n\n".join([chunk for page in pages for chunk in page])
    return model_fn(all_text)
