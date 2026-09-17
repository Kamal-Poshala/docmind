import json

from sqlalchemy.orm import Session

from app.db.models import Document
from app.rag.retriever import retrieve

TOOL_DEFINITIONS = [
    {
        "name": "search_documents",
        "description": (
            "Search the user's uploaded documents for passages relevant to a query. "
            "Use this whenever answering a question that might depend on document content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "top_k": {"type": "integer", "description": "Number of passages to return", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_documents",
        "description": "List the documents currently uploaded, so you know what is available to search.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def run_tool(db: Session, name: str, tool_input: dict) -> str:
    if name == "search_documents":
        chunks = retrieve(db, tool_input["query"], top_k=tool_input.get("top_k", 5))
        if not chunks:
            return "No relevant passages found."
        results = [
            {"document_id": str(chunk.document_id), "content": chunk.content}
            for chunk in chunks
        ]
        return json.dumps(results)

    if name == "list_documents":
        documents = db.query(Document).order_by(Document.created_at.desc()).all()
        return json.dumps([{"id": str(doc.id), "filename": doc.filename} for doc in documents])

    raise ValueError(f"Unknown tool: {name}")
