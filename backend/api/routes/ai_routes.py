from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.ai_service import ask_ai


router = APIRouter()


class AIChatRequest(BaseModel):
    prompt: str


@router.post("/ai-chat")
def ai_chat(payload: AIChatRequest):
    result = ask_ai(payload.prompt)
    return {"response": result}