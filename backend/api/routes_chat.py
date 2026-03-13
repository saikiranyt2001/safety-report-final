from fastapi import APIRouter, Depends
from backend.rag.rag_engine import RAGEngine
from backend.core.rbac import require_roles

router = APIRouter()

@router.post("/chat")
async def chat(
    data: dict,
    _user=Depends(require_roles("admin", "manager", "worker")),
):

    message = data.get("message", "")
    rag = RAGEngine()
    answer = rag.answer_query(message)
    context = rag.retrieve(message)

    return {
        "reply": answer,
        "sources": [
            {
                "category": item.get("category", "General"),
                "reference": item.get("reference", "Ref N/A"),
            }
            for item in context
        ],
    }