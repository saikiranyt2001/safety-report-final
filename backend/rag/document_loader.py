import os

DOCS_PATH = "backend/rag/documents"

def load_documents():
    documents = []
    if not os.path.exists(DOCS_PATH):
        return []
    for file in os.listdir(DOCS_PATH):
        if file.endswith(".txt"):
            with open(os.path.join(DOCS_PATH, file), "r", encoding="utf-8") as f:
                documents.append(f.read())
    return documents
