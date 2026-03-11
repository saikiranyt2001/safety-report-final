# Simple Vector Store for Regulation RAG

class VectorStore:

    def __init__(self, documents):
        self.documents = documents

    def similarity_search(self, query, k=3):
        query = query.lower()
        scored = []
        for doc in self.documents:
            text = doc["regulation"].lower()
            score = sum(word in text for word in query.split())
            scored.append((score, doc))
        scored.sort(reverse=True, key=lambda x: x[0])
        results = [doc for score, doc in scored if score > 0]
        return results[:k]
