from collections.abc import Generator

from sqlalchemy.orm import Session

from app.agents.llm import ToolCall, TurnEnd
from app.agents.tools import TOOL_DEFINITIONS, run_tool

SYSTEM_PROMPT = (
    "You are DocMind, an assistant that answers questions grounded in the user's uploaded "
    "documents. Use the search_documents tool before answering anything that might depend on "
    "document content, and use list_documents if the user asks what's available. If the "
    "documents don't contain the answer, say so honestly instead of guessing."
)

MAX_TOOL_ROUNDS = 5


def _execute_tool(db: Session, call: ToolCall) -> str:
    try:
        return run_tool(db, call.name, call.input)
    except Exception as exc:
        return f"Error running tool {call.name}: {exc}"


def stream_agent_reply(db: Session, messages: list[dict], provider) -> Generator[str, None, None]:
    conversation = list(messages)

    for _ in range(MAX_TOOL_ROUNDS):
        turn = None
        for event in provider.stream_turn(SYSTEM_PROMPT, conversation, TOOL_DEFINITIONS):
            if isinstance(event, TurnEnd):
                turn = event
            else:
                yield event

        conversation.append(
            {"role": "assistant", "content": turn.text, "tool_calls": turn.tool_calls}
        )
        if not turn.tool_calls:
            return

        for call in turn.tool_calls:
            conversation.append(
                {"role": "tool", "tool_call_id": call.id, "content": _execute_tool(db, call)}
            )

    yield "\n\n[Stopped: the assistant made too many tool calls without answering.]"
