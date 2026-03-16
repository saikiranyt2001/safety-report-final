import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.rag.rag_engine import RAGEngine


def test_smalltalk_does_not_return_random_regulation():
    rag = RAGEngine()
    response = rag.answer_query("how are you")
    assert "Chemical storage areas" not in response
    assert "ready to help" in response
