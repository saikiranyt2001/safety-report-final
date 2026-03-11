from fastapi import APIRouter
from backend.agents.orchestrator import run_safety_pipeline
from backend.rag.rag_engine import RAGEngine

router = APIRouter()

@router.post("/chat")
async def chat(data: dict):

    message = data.get("message", "")

    # Run safety AI pipeline
    pipeline_result = run_safety_pipeline(
        site_type="construction",
        site_data={"description": message}
    )

    # Retrieve safety knowledge (RAG)
    rag = RAGEngine()
    context = rag.retrieve(message)

    response = {
        "analysis": pipeline_result,
        "knowledge": context
    }

    return {
        "reply": response
    }