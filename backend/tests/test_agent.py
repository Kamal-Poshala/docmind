from types import SimpleNamespace

from app.agents import agent


class FakeBlock:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def model_dump(self):
        return dict(self.__dict__)


class FakeStream:
    def __init__(self, texts, message):
        self.text_stream = iter(texts)
        self._message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._message


class FakeAnthropic:
    """Scripted stand-in: each messages.stream() call returns the next scripted turn."""

    def __init__(self, turns):
        self._turns = iter(turns)
        self.calls = []
        self.messages = SimpleNamespace(stream=self._stream)

    def _stream(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        texts, message = next(self._turns)
        return FakeStream(texts, message)


def install_fake_client(monkeypatch, turns):
    fake = FakeAnthropic(turns)
    monkeypatch.setattr(agent, "Anthropic", lambda api_key: fake)
    return fake


def test_plain_answer_streams_and_stops(monkeypatch):
    message = SimpleNamespace(stop_reason="end_turn", content=[FakeBlock(type="text", text="Hi there")])
    fake = install_fake_client(monkeypatch, [(["Hi ", "there"], message)])

    tokens = list(agent.stream_agent_reply(db=None, messages=[{"role": "user", "content": "hello"}]))

    assert tokens == ["Hi ", "there"]
    assert len(fake.calls) == 1


def test_tool_call_is_executed_then_answer_streams(monkeypatch):
    tool_use = FakeBlock(
        type="tool_use", id="tool_1", name="search_documents", input={"query": "refund policy"}
    )
    first = SimpleNamespace(stop_reason="tool_use", content=[tool_use])
    second = SimpleNamespace(
        stop_reason="end_turn", content=[FakeBlock(type="text", text="Refunds take 5 days.")]
    )
    fake = install_fake_client(monkeypatch, [([], first), (["Refunds take 5 days."], second)])

    executed = []

    def fake_run_tool(db, name, tool_input):
        executed.append((name, tool_input))
        return '[{"content": "Refunds are processed within 5 days."}]'

    monkeypatch.setattr(agent, "run_tool", fake_run_tool)

    tokens = list(
        agent.stream_agent_reply(db=None, messages=[{"role": "user", "content": "refund policy?"}])
    )

    assert tokens == ["Refunds take 5 days."]
    assert executed == [("search_documents", {"query": "refund policy"})]
    assert len(fake.calls) == 2

    tool_result_message = fake.calls[1]["messages"][-1]
    assert tool_result_message["role"] == "user"
    assert tool_result_message["content"][0]["type"] == "tool_result"
    assert tool_result_message["content"][0]["tool_use_id"] == "tool_1"
