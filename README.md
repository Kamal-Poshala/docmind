# DocMind

DocMind is a full-stack AI assistant that answers questions grounded in documents you upload. It combines retrieval-augmented generation (RAG) with an agentic tool-use loop: instead of always stuffing retrieved text into the prompt, the model decides for itself when to search your documents, via a real tool call, and streams its answer back token by token.

## Why this project exists

This is a portfolio project built to demonstrate:

- **Full-stack engineering**: a Next.js/TypeScript frontend talking to a FastAPI/Python backend, backed by Postgres.
- **Applied LLM engineering**: agentic tool-calling (not just a single prompt-and-response wrapper), streaming responses, and a vector-search pipeline built from first principles (no LangChain black box).
- **ML fundamentals**: local sentence-embedding model for retrieval, chunking strategy, and a real vector index (pgvector) with cosine similarity search.

## Architecture

```
frontend (Next.js)  --->  backend (FastAPI)  --->  Anthropic API (Claude, tool use)
                                |
                                v
                          Postgres + pgvector
                          (documents, chunks, embeddings)
```

1. A document is uploaded, text is extracted (PDF/plain text), split into overlapping chunks, embedded locally with `sentence-transformers`, and stored in Postgres with `pgvector`.
2. A chat message is sent to the backend, which runs an agent loop against the Anthropic API: the model can call a `search_documents` tool (vector similarity search) or `list_documents` before answering.
3. The final answer streams back to the frontend over HTTP as it's generated.

## Tech stack

| Layer      | Tech |
|------------|------|
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS |
| Backend    | FastAPI, SQLAlchemy |
| LLM        | Anthropic API (Claude), tool use / agent loop |
| Embeddings | `sentence-transformers` (local, no API key needed) |
| Vector DB  | Postgres + `pgvector` |

## Running locally

**1. Start Postgres (with pgvector):**

```bash
docker compose up -d
```

**2. Backend:**

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env   # then add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

**3. Frontend:**

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000, upload a PDF or text file, and start asking questions about it.

## Project structure

```
docmind/
  backend/
    app/
      agents/     # tool definitions + Claude tool-use loop
      api/        # FastAPI routers (documents, chat)
      core/       # settings
      db/         # SQLAlchemy models + session
      rag/        # chunking, embeddings, retrieval, ingestion
    tests/
  frontend/
    src/
      app/            # Next.js App Router pages
      components/     # chat UI, document panel
      lib/            # API client
  docker-compose.yml  # Postgres + pgvector
```

## Possible next steps

- Add authentication and per-user document isolation for a real multi-tenant deployment.
- Add an eval harness that scores retrieval quality and answer faithfulness over a fixed test set.
- Support additional file types (DOCX, HTML) and OCR for scanned PDFs.
