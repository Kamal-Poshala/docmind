from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.agent import stream_agent_reply
from app.db.session import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


@router.post("/stream")
def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    messages = [{"role": m.role, "content": m.content} for m in request.history]
    messages.append({"role": "user", "content": request.message})

    def event_source():
        for token in stream_agent_reply(db, messages):
            yield token

    return StreamingResponse(event_source(), media_type="text/plain")
