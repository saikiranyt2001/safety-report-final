# Simple Vector Store for Regulation RAG

class VectorStore:
    """
    Simple similarity search engine for regulations.
    This simulates vector search using keyword matching.
    """

    def __init__(self, documents):
        self.documents = documents

    def similarity_search(self, query, k=3):
        """
        Return top-k most relevant regulations
        """

        if not query:
            return []

        query_words = query.lower().split()
        scored_results = []

        for doc in self.documents:

            text = doc.get("regulation", "").lower()

            # basic keyword match scoring
            score = sum(1 for word in query_words if word in text)

            scored_results.append((score, doc))

        # sort by highest score
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # filter only relevant docs
        results = [doc for score, doc in scored_results if score > 0]

        return results[:k]