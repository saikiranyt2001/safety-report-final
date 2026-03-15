from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.rag.rag_engine import RAGEngine
from backend.core.rbac import require_roles

router = APIRouter()

class ChatPayload(BaseModel):
    message: str | None = None
    prompt: str | None = None


class RagPayload(BaseModel):
    context: str


@router.post("/chat")
async def chat(
    data: ChatPayload,
    _user=Depends(require_roles("admin", "manager", "worker")),
):
    message = (data.message or data.prompt or "").strip()
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


@router.post("/ai-chat")
async def ai_chat(
    data: ChatPayload,
    _user=Depends(require_roles("admin", "manager", "worker")),
):
    message = (data.prompt or data.message or "").strip()
    rag = RAGEngine()
    return {"response": rag.answer_query(message)}


@router.post("/rag-report")
async def rag_report(
    data: RagPayload,
    _user=Depends(require_roles("admin", "manager", "worker")),
):
    rag = RAGEngine()
    report = rag.answer_query(data.context.strip())
    return {"report": report}
