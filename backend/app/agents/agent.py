from collections.abc import Generator

from anthropic import Anthropic
from sqlalchemy.orm import Session

from app.agents.tools import TOOL_DEFINITIONS, run_tool
from app.core.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = (
    "You are DocMind, an assistant that answers questions grounded in the user's uploaded "
    "documents. Use the search_documents tool before answering anything that might depend on "
    "document content, and use list_documents if the user asks what's available. If the "
    "documents don't contain the answer, say so honestly instead of guessing."
)


def stream_agent_reply(db: Session, messages: list[dict]) -> Generator[str, None, None]:
    client = Anthropic(api_key=settings.anthropic_api_key)
    conversation = list(messages)

    while True:
        final_message = None
        with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation,
            tools=TOOL_DEFINITIONS,
        ) as stream:
            for text in stream.text_stream:
                yield text
            final_message = stream.get_final_message()

        conversation.append(
            {"role": "assistant", "content": [block.model_dump() for block in final_message.content]}
        )

        if final_message.stop_reason != "tool_use":
            break

        tool_results = []
        for block in final_message.content:
            if block.type == "tool_use":
                result = run_tool(db, block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
        conversation.append({"role": "user", "content": tool_results})
