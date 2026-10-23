# Daleel · دليل

**Ask your documents questions in Arabic or English, and get answers that cite the exact page they came from.**

Upload a long PDF (a university handbook, a company policy, a regulation), ask a question in plain language, and Daleel answers using only that document. Every answer points to the page and passage it is based on, and when the document does not contain the answer, Daleel says so instead of guessing.

> **Status:** Phases 1 and 2 of 3 are complete: accounts, and uploading PDFs that are processed and indexed for semantic search. Asking questions and getting cited answers is Phase 3. See [Roadmap](#roadmap). Nothing below claims a feature that is not implemented yet.

## Why this project

Most "chat with your PDF" demos are English-only and happily invent answers. Daleel focuses on two things they skip:

- **Arabic first.** The interface is right-to-left Arabic, and the document pipeline is designed for Arabic text (normalisation, multilingual embeddings, Arabic evaluation questions).
- **Verifiable answers.** Answers are grounded in retrieved passages, citations are validated against what was actually retrieved, and retrieval quality is measured with an evaluation set rather than assumed.

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript (strict), Tailwind CSS 4, TanStack Query |
| API client | Generated from the backend's OpenAPI schema (`openapi-typescript` + `openapi-fetch`) |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 |
| Database | PostgreSQL 16 + pgvector (HNSW index), migrations with Alembic |
| Documents | PyMuPDF (text + positions), Arabic normalisation, page-aware chunking |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` run locally with fastembed (ONNX, CPU, free) |
| Background jobs | Postgres job table + worker using `SELECT … FOR UPDATE SKIP LOCKED` |
| Auth | Argon2id password hashing, JWT in an `httpOnly` `SameSite=Lax` cookie |
| Testing | pytest (against real Postgres), Playwright end-to-end tests (desktop + phone) |
| Tooling | uv, Ruff, ESLint, GitHub Actions, Docker Compose |

## Architecture

```mermaid
flowchart LR
    Browser["Browser<br/>(Next.js pages, RTL Arabic UI)"]
    Next["Next.js server<br/>proxy.ts redirects<br/>/api/* rewrite"]
    API["FastAPI<br/>routes → services → repositories"]
    Worker["Worker<br/>extract → chunk → embed"]
    DB[("PostgreSQL + pgvector")]
    Files[("File storage")]

    Browser -- "same-origin requests<br/>session cookie" --> Next
    Next -- "/api/*" --> API
    API -- "document + job<br/>(one transaction)" --> DB
    API -- "PDF" --> Files
    Worker -- "claim job<br/>SKIP LOCKED" --> DB
    Files --> Worker
    Worker -- "chunks + vectors" --> DB
```

- The browser only talks to the Next.js origin. Next.js forwards `/api/*` to FastAPI, so the session cookie is same-origin and no CORS configuration is needed.
- The backend is layered: **routes** handle HTTP, **services** hold the rules (e.g. registration, login), **repositories** are the only code that queries tables.
- All errors use one JSON shape: `{"error": {"code", "message", "details"?}}`. Unexpected errors are logged server-side and never leak internals to the client.

### Document pipeline

Uploading returns immediately; the expensive work happens in a background worker:

1. **Validate at upload:** checks the file's bytes (not its name) are a PDF, rejects encrypted, oversized (20 MB) or very long (500 pages) files. The stored file is named by the server (`<user id>/<document id>.pdf`), never by the user.
2. **Queue:** the document row and its processing job are committed in the same transaction.
3. **Claim:** a worker takes the oldest job with `SELECT … FOR UPDATE SKIP LOCKED`, so several workers never process the same job. Jobs left "running" by a crashed worker are re-queued.
4. **Extract:** PyMuPDF reads text blocks with their positions. PDFs with no text layer (scans) fail with a clear `scanned_pdf` code.
5. **Normalise:** NFKC turns Arabic "presentation form" characters (common in PDFs) back into normal letters. A second, search-only form also removes diacritics and tatweel and unifies alef, ya and ta marbuta variants.
6. **Chunk:** passages of up to 450 characters with overlap, never crossing a page, each keeping its page number and rectangles for highlighting. The size comes from a measurement: the model reads at most 128 tokens (~3.9 Arabic characters per token), and larger chunks were being silently truncated.
7. **Embed and save:** vectors are computed outside any transaction, then chunks are replaced and the document marked `ready` in one short transaction. Retries never duplicate chunks; a document deleted mid-processing is discarded safely.

Failures are recorded as stable codes (shown in Arabic by the UI). Transient errors are retried up to 3 times; permanent ones (e.g. a scanned PDF) fail immediately and the user can retry manually.

## Run it locally

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 22+, and either Docker or a local PostgreSQL 16 with pgvector.

```bash
# 1. Database (creates "daleel" and "daleel_test")
docker compose up -d

# 2. Backend  → http://localhost:8000/api/docs
cd backend
cp .env.example .env          # then set JWT_SECRET
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
#    The first processed document downloads the embedding model (~220 MB, once).

# 3. Frontend → http://localhost:3000   (in a second terminal)
cd frontend
npm install
npm run dev
```

## Tests and checks

```bash
# Backend: lint, format, tests (real Postgres), models vs migrations
cd backend
uv run ruff check . && uv run ruff format --check .
uv run pytest
uv run alembic check
RUN_MODEL_TESTS=1 uv run pytest tests/test_local_model.py   # optional: real model, real retrieval

# Frontend: lint, type check, production build
cd frontend
npm run lint && npm run typecheck && npm run build

# End-to-end (backend must be running on :8000; builds are served on :3000)
npm run test:e2e
```

CI runs all of the above on every push, and also fails if the frontend's generated API types are out of date with the backend.

When you change the API:

```bash
cd backend && uv run python -m scripts.export_openapi   # writes frontend/openapi.json
cd ../frontend && npm run api:types                      # regenerates src/lib/api/schema.d.ts
```

## Project structure

```
backend/
  app/
    api/routes/      HTTP endpoints (auth, documents, health)
    api/deps.py      shared dependencies (DB session, current user)
    core/            settings, security (hashing, tokens), error handling
    db/              engine, session, declarative base
    models/          SQLAlchemy models
    repositories/    database queries
    schemas/         Pydantic request/response models
    services/        business rules and the document pipeline
    worker.py        standalone worker for production
  alembic/           migrations
  scripts/           OpenAPI export, sample PDF generator
  tests/
frontend/
  src/app/           pages (landing, login, register, dashboard)
  src/components/    UI primitives
  src/features/      feature modules (auth, documents)
  src/lib/api/       generated types + typed client
  src/proxy.ts       optimistic auth redirects
  e2e/               Playwright tests
docs/                spec, interview guide
samples/             a fictional Arabic/English student guide for demos and tests
```

Try it with `samples/daleel-sample-guide.pdf`: a four-page guide for an invented university, mostly Arabic with one English page.

## Roadmap

- [x] **Phase 1 · Foundation:** project setup, database and migrations, secure email/password auth, Arabic RTL interface, unit + integration + E2E tests, CI.
- [x] **Phase 2 · Documents:** PDF upload and validation, background processing worker (Postgres job queue), Arabic-aware text extraction and chunking, embeddings stored in pgvector, document library with live processing status.
- [ ] **Phase 3 · Answers:** hybrid search (vector + keyword), question answering with validated page citations, source viewer that opens the cited page, conversation history, retrieval evaluation (Recall@K, MRR, refusal on unanswerable questions), deployment guide.

## Known limitations

- Questions and answers are not built yet (Phase 3).
- Scanned PDFs (images of text) are rejected; there is no OCR yet.
- Some right-to-left PDFs extract parentheses mirrored, e.g. `)text(`. Display only; search ignores punctuation.
- With vector search alone, the small model misses some dialect questions (e.g. "كم نسبة الغياب اللي تحرمني من الاختبار؟" does not find the attendance rule). Tracked as an expected failure in `tests/test_local_model.py`; Phase 3's hybrid keyword + vector search targets it.
- In development the worker runs inside the API process. In production, run it separately (`RUN_WORKER_IN_API=false`, `uv run python -m app.worker`).
- Login has no rate limiting yet (planned alongside the AI endpoints in Phase 3).
- No email verification or password reset.
