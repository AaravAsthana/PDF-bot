from llama_cloud_services import LlamaParse
from langchain.text_splitter import RecursiveCharacterTextSplitter
from configuration import LLAMA_CLOUD_API_KEY

def parse_pdf(path: str):
    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY,
        num_workers=4,
        verbose=False,
        language="en"
    )
    result = parser.parse(path)
    # get text pages
    pages = result.get_text_documents(split_by_page=True)

    # Paragraph splitter: double newline
    chunks = []
    for doc in pages:
        text = doc.text.strip()
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        # merge small paras
        merged = []
        buffer = ""
        for p in paras:
            if buffer and len(buffer) < 200:
                buffer += "\n\n" + p
            else:
                if buffer:
                    merged.append(buffer)
                buffer = p
        if buffer:
            merged.append(buffer)

        # add to chunks with metadata
        for part in merged:
            chunks.append({
                "page_content": part,
                "metadata": {
                    **doc.metadata, 
                    "page": doc.metadata.get("page", None)
                }
            })
    return chunks
