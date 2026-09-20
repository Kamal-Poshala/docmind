import json
import uuid
from types import SimpleNamespace

import pytest

from app.agents import tools


def test_unknown_tool_raises():
    with pytest.raises(ValueError, match="Unknown tool"):
        tools.run_tool(db=None, name="does_not_exist", tool_input={})


def test_search_documents_returns_json_passages(monkeypatch):
    doc_id = uuid.uuid4()
    fake_chunks = [SimpleNamespace(document_id=doc_id, content="Paris is the capital of France.")]
    monkeypatch.setattr(tools, "retrieve", lambda db, query, top_k=5: fake_chunks)

    result = json.loads(tools.run_tool(None, "search_documents", {"query": "capital of France"}))

    assert result == [{"document_id": str(doc_id), "content": "Paris is the capital of France."}]


def test_search_documents_handles_no_results(monkeypatch):
    monkeypatch.setattr(tools, "retrieve", lambda db, query, top_k=5: [])

    result = tools.run_tool(None, "search_documents", {"query": "anything"})

    assert result == "No relevant passages found."


def test_tool_definitions_have_required_schema_fields():
    for definition in tools.TOOL_DEFINITIONS:
        assert {"name", "description", "input_schema"} <= definition.keys()
