# DocMind

DocMind is a full-stack AI assistant that answers questions grounded in documents you upload. It combines retrieval-augmented generation (RAG) with an agentic tool-use loop: instead of always stuffing retrieved text into the prompt, the model decides for itself when to search your documents, via a real tool call, and streams its answer back token by token.

## Why this project exists

This is a portfolio project built to demonstrate:

- **Full-stack engineering**: a Next.js/TypeScript frontend talking to a FastAPI/Python backend, backed by Postgres.
- **Applied LLM engineering**: agentic tool-calling (not just a single prompt-and-response wrapper), streaming responses, and a vector-search pipeline built from first principles (no LangChain black box).
- **ML fundamentals**: local sentence-embedding model for retrieval, chunking strategy, and a real vector index (pgvector) with cosine similarity search.

## Architecture

```
frontend (Next.js)  --->  backend (FastAPI)  --->  LLM provider (Gemini by default, tool use)
                                |
                                v
                          Postgres + pgvector
                          (documents, chunks, embeddings)
```

1. A document is uploaded, text is extracted (PDF/plain text), split into overlapping chunks, embedded locally with `sentence-transformers`, and stored in Postgres with `pgvector`.
2. A chat message is sent to the backend, which runs an agent loop against the configured LLM provider: the model can call a `search_documents` tool (vector similarity search) or `list_documents` before answering.
3. The final answer streams back to the frontend over HTTP as it's generated.

## Tech stack

| Layer      | Tech |
|------------|------|
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS |
| Backend    | FastAPI, SQLAlchemy |
| LLM        | Provider-agnostic tool-use agent loop: Gemini (default, free tier), Anthropic, Groq, OpenRouter, Ollama, or any OpenAI-compatible API |
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
cp .env.example .env   # then add your LLM_API_KEY (see "Choosing an LLM provider")
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

### Or run the whole stack in Docker

Once `backend/.env` has a real `LLM_API_KEY`, `docker compose up -d --build` builds and runs Postgres, the backend, and the frontend together (see `backend/Dockerfile`, `frontend/Dockerfile`). This is closer to how you'd deploy it; the steps above are better for day-to-day development since they give you hot reload.

## Choosing an LLM provider

The agent loop is provider-agnostic. Set `LLM_PROVIDER` in `backend/.env`:

| `LLM_PROVIDER`      | Key from | Default model |
|---------------------|----------|---------------|
| `gemini` (default)  | [Google AI Studio](https://aistudio.google.com/apikey), has a free tier | `gemini-3.5-flash-lite` |
| `anthropic`         | [Anthropic Console](https://console.anthropic.com) (paid) | `claude-sonnet-5` |
| `groq`              | [Groq Console](https://console.groq.com) | set `LLM_MODEL` |
| `openrouter`        | [OpenRouter](https://openrouter.ai) | set `LLM_MODEL` |
| `ollama`            | none (runs locally) | set `LLM_MODEL` (a tool-calling model, e.g. `llama3.1`) |
| `openai_compatible` | any | set `LLM_MODEL` and `LLM_BASE_URL` |

`LLM_MODEL` and `LLM_BASE_URL` override the defaults for any provider. Model lineups change often, so check the provider's docs if a default is rejected.

## Project structure

```
docmind/
  backend/
    app/
      agents/     # tool definitions, provider-agnostic agent loop, LLM providers
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

## Evaluating retrieval quality

`backend/eval/retrieval_eval.py` runs a fixed set of queries against a small in-memory corpus and checks that the expected document is retrieved (hit_rate@3), using the real chunking and embedding pipeline. It needs no Postgres or LLM key, so it also runs as a normal test in CI (`tests/test_eval_retrieval.py`). Run it directly with:

```bash
cd backend && python -m eval.retrieval_eval
```

## Possible next steps

- Add authentication and per-user document isolation for a real multi-tenant deployment.
- Extend the eval harness to score answer faithfulness (e.g. LLM-as-judge) over full chat turns, not just retrieval.
- Support additional file types (DOCX, HTML) and OCR for scanned PDFs.
