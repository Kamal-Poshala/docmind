import json
from collections.abc import Iterator
from dataclasses import dataclass, field

from anthropic import Anthropic
from openai import OpenAI

from app.core.config import Settings, get_settings

ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-5"

# provider name -> (base_url, default_model); None means the user must set LLM_MODEL
OPENAI_COMPATIBLE_PRESETS: dict[str, tuple[str, str | None]] = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-3.5-flash-lite"),
    "groq": ("https://api.groq.com/openai/v1", None),
    "openrouter": ("https://openrouter.ai/api/v1", None),
    "ollama": ("http://localhost:11434/v1", None),
    "openai_compatible": ("", None),
}


class LLMConfigError(Exception):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict
    extra: dict | None = None


@dataclass
class TurnEnd:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


# Neutral conversation format shared by all providers:
#   {"role": "user" | "assistant", "content": str, "tool_calls": list[ToolCall] (optional)}
#   {"role": "tool", "tool_call_id": str, "content": str}


def _to_anthropic_messages(messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    for message in messages:
        if message["role"] == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": message["tool_call_id"],
                "content": message["content"],
            }
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
        elif message["role"] == "assistant" and message.get("tool_calls"):
            blocks = []
            if message["content"]:
                blocks.append({"type": "text", "text": message["content"]})
            blocks.extend(
                {"type": "tool_use", "id": call.id, "name": call.name, "input": call.input}
                for call in message["tool_calls"]
            )
            out.append({"role": "assistant", "content": blocks})
        else:
            out.append({"role": message["role"], "content": message["content"]})
    return out


def _to_openai_messages(system: str, messages: list[dict]) -> list[dict]:
    out: list[dict] = [{"role": "system", "content": system}]
    for message in messages:
        if message["role"] == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": message["tool_call_id"],
                    "content": message["content"],
                }
            )
        elif message["role"] == "assistant" and message.get("tool_calls"):
            tool_calls = []
            for call in message["tool_calls"]:
                entry = {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.input)},
                }
                if call.extra:
                    entry.update(call.extra)
                tool_calls.append(entry)
            out.append(
                {"role": "assistant", "content": message["content"] or None, "tool_calls": tool_calls}
            )
        else:
            out.append({"role": message["role"], "content": message["content"]})
    return out


def _to_openai_tool(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _find_slot(pending: list[dict], delta) -> dict:
    # OpenAI streams a call as one id-bearing chunk followed by index-only argument
    # fragments; some compatible servers send each call whole, so match by id first.
    if delta.id:
        for slot in pending:
            if slot["id"] == delta.id:
                return slot
    else:
        for slot in reversed(pending):
            if slot["index"] == delta.index:
                return slot
    slot = {"index": delta.index, "id": delta.id or "", "name": "", "args": "", "extra": None}
    pending.append(slot)
    return slot


class AnthropicProvider:
    def __init__(self, api_key: str, model: str):
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def stream_turn(self, system: str, messages: list[dict], tools: list[dict]) -> Iterator:
        with self._client.messages.stream(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=_to_anthropic_messages(messages),
            tools=tools,
        ) as stream:
            for text in stream.text_stream:
                yield text
            final = stream.get_final_message()

        text = "".join(block.text for block in final.content if block.type == "text")
        calls = [
            ToolCall(id=block.id, name=block.name, input=block.input)
            for block in final.content
            if block.type == "tool_use"
        ]
        yield TurnEnd(text=text, tool_calls=calls)


class OpenAICompatibleProvider:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def stream_turn(self, system: str, messages: list[dict], tools: list[dict]) -> Iterator:
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=_to_openai_messages(system, messages),
            tools=[_to_openai_tool(tool) for tool in tools],
            stream=True,
        )

        text_parts: list[str] = []
        pending: list[dict] = []
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                text_parts.append(delta.content)
                yield delta.content
            for tool_delta in delta.tool_calls or []:
                slot = _find_slot(pending, tool_delta)
                if tool_delta.function:
                    if tool_delta.function.name:
                        slot["name"] = tool_delta.function.name
                    if tool_delta.function.arguments:
                        slot["args"] += tool_delta.function.arguments
                extra = (tool_delta.model_extra or {}).get("extra_content")
                if extra:
                    slot["extra"] = {"extra_content": extra}

        calls = []
        for position, slot in enumerate(pending):
            try:
                arguments = json.loads(slot["args"]) if slot["args"] else {}
            except json.JSONDecodeError:
                arguments = {}
            calls.append(
                ToolCall(
                    id=slot["id"] or f"call_{position}",
                    name=slot["name"],
                    input=arguments,
                    extra=slot["extra"],
                )
            )
        yield TurnEnd(text="".join(text_parts), tool_calls=calls)


def get_provider(settings: Settings | None = None):
    settings = settings or get_settings()
    name = settings.llm_provider.strip().lower()

    if name == "anthropic":
        if not settings.llm_api_key:
            raise LLMConfigError("LLM_API_KEY is not set (LLM_PROVIDER=anthropic).")
        return AnthropicProvider(settings.llm_api_key, settings.llm_model or ANTHROPIC_DEFAULT_MODEL)

    if name not in OPENAI_COMPATIBLE_PRESETS:
        supported = ", ".join(["anthropic", *OPENAI_COMPATIBLE_PRESETS])
        raise LLMConfigError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use one of: {supported}.")

    preset_url, preset_model = OPENAI_COMPATIBLE_PRESETS[name]
    base_url = settings.llm_base_url or preset_url
    model = settings.llm_model or preset_model
    if not base_url:
        raise LLMConfigError(f"LLM_BASE_URL is required for LLM_PROVIDER={name}.")
    if not model:
        raise LLMConfigError(f"LLM_MODEL is required for LLM_PROVIDER={name}.")

    api_key = settings.llm_api_key
    if not api_key:
        if name != "ollama":
            raise LLMConfigError(f"LLM_API_KEY is not set (LLM_PROVIDER={name}).")
        api_key = "ollama"

    return OpenAICompatibleProvider(api_key, base_url, model)
