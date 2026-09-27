import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.agent import stream_agent_reply
from app.agents.llm import LLMConfigError, get_provider
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


@router.post("/stream")
def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        provider = get_provider()
    except LLMConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    messages = [{"role": m.role, "content": m.content} for m in request.history]
    messages.append({"role": "user", "content": request.message})

    def event_source():
        try:
            yield from stream_agent_reply(db, messages, provider)
        except Exception:
            logger.exception("Chat stream failed")
            yield (
                "\n\n[The model request failed. Check the backend logs; "
                "free-tier providers may be rate limiting.]"
            )

    return StreamingResponse(event_source(), media_type="text/plain")
