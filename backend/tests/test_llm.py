from types import SimpleNamespace

import pytest

from app.agents import llm
from app.agents.llm import LLMConfigError, ToolCall, TurnEnd
from app.core.config import Settings

TOOLS = [
    {
        "name": "search_documents",
        "description": "Search docs",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
    }
]


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


# --- message conversion -----------------------------------------------------


def tool_exchange():
    call = ToolCall(id="c1", name="search_documents", input={"query": "x"})
    return [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "Let me look.", "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "c1", "content": "result one"},
    ]


def test_anthropic_conversion_uses_content_blocks():
    converted = llm._to_anthropic_messages(tool_exchange())

    assert converted[0] == {"role": "user", "content": "question"}
    assert converted[1]["content"] == [
        {"type": "text", "text": "Let me look."},
        {"type": "tool_use", "id": "c1", "name": "search_documents", "input": {"query": "x"}},
    ]
    assert converted[2] == {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": "c1", "content": "result one"}],
    }


def test_anthropic_merges_consecutive_tool_results_into_one_user_message():
    messages = tool_exchange() + [{"role": "tool", "tool_call_id": "c2", "content": "result two"}]

    converted = llm._to_anthropic_messages(messages)

    assert len(converted) == 3
    assert [b["tool_use_id"] for b in converted[2]["content"]] == ["c1", "c2"]


def test_openai_conversion_uses_tool_calls_and_system_message():
    converted = llm._to_openai_messages("be helpful", tool_exchange())

    assert converted[0] == {"role": "system", "content": "be helpful"}
    assistant = converted[2]
    assert assistant["tool_calls"] == [
        {
            "id": "c1",
            "type": "function",
            "function": {"name": "search_documents", "arguments": '{"query": "x"}'},
        }
    ]
    assert converted[3] == {"role": "tool", "tool_call_id": "c1", "content": "result one"}


def test_openai_conversion_echoes_provider_extras_on_tool_calls():
    call = ToolCall(
        id="c1",
        name="search_documents",
        input={},
        extra={"extra_content": {"google": {"thought_signature": "abc"}}},
    )
    messages = [{"role": "assistant", "content": "", "tool_calls": [call]}]

    converted = llm._to_openai_messages("sys", messages)

    tool_call = converted[1]["tool_calls"][0]
    assert tool_call["extra_content"] == {"google": {"thought_signature": "abc"}}
    assert converted[1]["content"] is None


def test_openai_tool_schema_conversion():
    assert llm._to_openai_tool(TOOLS[0]) == {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search docs",
            "parameters": TOOLS[0]["input_schema"],
        },
    }


# --- OpenAI-compatible streaming ---------------------------------------------


def text_chunk(text):
    delta = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def tool_chunk(index, id=None, name=None, arguments=None, extra=None):
    function = SimpleNamespace(name=name, arguments=arguments)
    tool = SimpleNamespace(
        index=index,
        id=id,
        function=function,
        model_extra={"extra_content": extra} if extra else {},
    )
    delta = SimpleNamespace(content=None, tool_calls=[tool])
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def make_provider(chunks):
    provider = llm.OpenAICompatibleProvider(api_key="k", base_url="http://localhost:1/v1", model="m")
    create = lambda **kwargs: iter(chunks)  # noqa: E731
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return provider


def run_turn(provider):
    events = list(provider.stream_turn("sys", [{"role": "user", "content": "hi"}], TOOLS))
    return events[:-1], events[-1]


def test_openai_streams_text_and_ignores_empty_choice_chunks():
    empty = SimpleNamespace(choices=[])
    provider = make_provider([empty, text_chunk("Hel"), text_chunk("lo")])

    tokens, end = run_turn(provider)

    assert tokens == ["Hel", "lo"]
    assert end == TurnEnd(text="Hello", tool_calls=[])


def test_openai_assembles_tool_call_from_fragments():
    provider = make_provider(
        [
            tool_chunk(0, id="call_a", name="search_documents", arguments=""),
            tool_chunk(0, arguments='{"query": '),
            tool_chunk(0, arguments='"refunds"}'),
        ]
    )

    tokens, end = run_turn(provider)

    assert tokens == []
    assert end.tool_calls == [
        ToolCall(id="call_a", name="search_documents", input={"query": "refunds"})
    ]


def test_openai_keeps_parallel_calls_sent_whole_with_same_index():
    provider = make_provider(
        [
            tool_chunk(0, id="a", name="search_documents", arguments='{"query": "one"}'),
            tool_chunk(0, id="b", name="search_documents", arguments='{"query": "two"}'),
        ]
    )

    _, end = run_turn(provider)

    assert [(c.id, c.input) for c in end.tool_calls] == [
        ("a", {"query": "one"}),
        ("b", {"query": "two"}),
    ]


def test_openai_generates_missing_ids_and_captures_extras():
    extra = {"google": {"thought_signature": "sig"}}
    provider = make_provider(
        [tool_chunk(0, name="list_documents", arguments="{}", extra=extra)]
    )

    _, end = run_turn(provider)

    call = end.tool_calls[0]
    assert call.id == "call_0"
    assert call.extra == {"extra_content": extra}


def test_openai_tolerates_invalid_tool_arguments():
    provider = make_provider([tool_chunk(0, id="a", name="search_documents", arguments="{oops")])

    _, end = run_turn(provider)

    assert end.tool_calls[0].input == {}


# --- provider selection -------------------------------------------------------


def test_gemini_is_the_default_provider_with_preset_url_and_model():
    provider = llm.get_provider(settings(llm_api_key="k"))

    assert isinstance(provider, llm.OpenAICompatibleProvider)
    assert provider._model == "gemini-3.5-flash-lite"
    assert "generativelanguage.googleapis.com" in str(provider._client.base_url)


def test_model_and_base_url_can_be_overridden():
    provider = llm.get_provider(
        settings(llm_api_key="k", llm_model="gemini-x", llm_base_url="http://example.test/v1/")
    )

    assert provider._model == "gemini-x"
    assert "example.test" in str(provider._client.base_url)


def test_anthropic_provider_uses_default_model():
    provider = llm.get_provider(settings(llm_provider="anthropic", llm_api_key="k"))

    assert isinstance(provider, llm.AnthropicProvider)
    assert provider._model == llm.ANTHROPIC_DEFAULT_MODEL


def test_ollama_needs_no_key_but_needs_a_model():
    with pytest.raises(LLMConfigError, match="LLM_MODEL"):
        llm.get_provider(settings(llm_provider="ollama"))

    provider = llm.get_provider(settings(llm_provider="ollama", llm_model="llama3.1"))
    assert isinstance(provider, llm.OpenAICompatibleProvider)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"llm_provider": "gemini"}, "LLM_API_KEY"),
        ({"llm_provider": "anthropic"}, "LLM_API_KEY"),
        ({"llm_provider": "groq", "llm_api_key": "k"}, "LLM_MODEL"),
        ({"llm_provider": "openai_compatible", "llm_api_key": "k", "llm_model": "m"}, "LLM_BASE_URL"),
        ({"llm_provider": "nonsense", "llm_api_key": "k"}, "Unknown LLM_PROVIDER"),
    ],
)
def test_misconfiguration_gives_clear_errors(overrides, message):
    with pytest.raises(LLMConfigError, match=message):
        llm.get_provider(settings(**overrides))
