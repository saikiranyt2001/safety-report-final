import os

DOCS_PATH = "backend/rag/documents"


def load_documents():
    """
    Load all .txt documents from the RAG documents folder.
    Returns a list of document texts.
    """

    documents = []

    # Check if folder exists
    if not os.path.exists(DOCS_PATH):
        print("⚠️ Documents folder not found:", DOCS_PATH)
        return documents

    # Read text files
    for file in os.listdir(DOCS_PATH):

        if file.endswith(".txt"):

            file_path = os.path.join(DOCS_PATH, file)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append(content)

            except Exception as e:
                print(f"❌ Error reading {file}: {e}")

    print(f"✅ Loaded {len(documents)} documents")

    return documents