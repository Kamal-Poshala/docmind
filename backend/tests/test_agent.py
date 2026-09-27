from app.agents import agent
from app.agents.llm import ToolCall, TurnEnd


class FakeProvider:
    """Scripted stand-in: each stream_turn() call replays the next scripted turn."""

    def __init__(self, turns):
        self._turns = iter(turns)
        self.calls = []

    def stream_turn(self, system, messages, tools):
        self.calls.append(list(messages))
        texts, end = next(self._turns)
        yield from texts
        yield end


def collect(provider, messages=None, db=None):
    messages = messages or [{"role": "user", "content": "hi"}]
    return list(agent.stream_agent_reply(db, messages, provider))


def test_plain_answer_streams_and_stops():
    provider = FakeProvider([(["Hi ", "there"], TurnEnd(text="Hi there"))])

    assert collect(provider) == ["Hi ", "there"]
    assert len(provider.calls) == 1


def test_tool_call_is_executed_and_result_fed_back(monkeypatch):
    call = ToolCall(id="tool_1", name="search_documents", input={"query": "refund policy"})
    provider = FakeProvider(
        [
            ([], TurnEnd(text="", tool_calls=[call])),
            (["Refunds take 5 days."], TurnEnd(text="Refunds take 5 days.")),
        ]
    )
    executed = []

    def fake_run_tool(db, name, tool_input):
        executed.append((name, tool_input))
        return "Refunds are processed within 5 days."

    monkeypatch.setattr(agent, "run_tool", fake_run_tool)

    assert collect(provider) == ["Refunds take 5 days."]
    assert executed == [("search_documents", {"query": "refund policy"})]

    second_call_messages = provider.calls[1]
    assert second_call_messages[-2]["role"] == "assistant"
    assert second_call_messages[-2]["tool_calls"] == [call]
    assert second_call_messages[-1] == {
        "role": "tool",
        "tool_call_id": "tool_1",
        "content": "Refunds are processed within 5 days.",
    }


def test_tool_errors_are_returned_to_the_model(monkeypatch):
    call = ToolCall(id="tool_1", name="search_documents", input={})
    provider = FakeProvider(
        [([], TurnEnd(text="", tool_calls=[call])), (["Sorry."], TurnEnd(text="Sorry."))]
    )

    def broken_tool(db, name, tool_input):
        raise KeyError("query")

    monkeypatch.setattr(agent, "run_tool", broken_tool)

    assert collect(provider) == ["Sorry."]
    tool_message = provider.calls[1][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["content"].startswith("Error running tool search_documents")


def test_tool_loop_is_capped(monkeypatch):
    call = ToolCall(id="tool_1", name="search_documents", input={"query": "x"})
    provider = FakeProvider(
        [([], TurnEnd(text="", tool_calls=[call])) for _ in range(agent.MAX_TOOL_ROUNDS)]
    )
    monkeypatch.setattr(agent, "run_tool", lambda db, name, tool_input: "result")

    output = collect(provider)

    assert len(provider.calls) == agent.MAX_TOOL_ROUNDS
    assert "too many tool calls" in "".join(output)
