# Daleel · دليل

**Ask your documents questions in Arabic or English, and get answers that cite the exact page they came from.**

Upload a long PDF (a university handbook, a company policy, a regulation), ask a question in plain language, and Daleel answers using only that document. Every answer points to the page and passage it is based on, and when the document does not contain the answer, Daleel says so instead of guessing.

> **Status:** Phase 1 of 3 is complete (foundation, authentication, CI). Document upload, search and cited answers are being built in Phases 2 and 3. See [Roadmap](#roadmap). Nothing below claims a feature that is not implemented yet.

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
| Database | PostgreSQL 16 + pgvector, migrations with Alembic |
| Auth | Argon2id password hashing, JWT in an `httpOnly` `SameSite=Lax` cookie |
| Testing | pytest (against real Postgres), Playwright end-to-end tests (desktop + phone) |
| Tooling | uv, Ruff, ESLint, GitHub Actions, Docker Compose |

## Architecture

```mermaid
flowchart LR
    Browser["Browser<br/>(Next.js pages, RTL Arabic UI)"]
    Next["Next.js server<br/>proxy.ts redirects<br/>/api/* rewrite"]
    API["FastAPI<br/>routes → services → repositories"]
    DB[("PostgreSQL + pgvector")]

    Browser -- "same-origin requests<br/>session cookie" --> Next
    Next -- "/api/*" --> API
    API --> DB
```

- The browser only talks to the Next.js origin. Next.js forwards `/api/*` to FastAPI, so the session cookie is same-origin and no CORS configuration is needed.
- The backend is layered: **routes** handle HTTP, **services** hold the rules (e.g. registration, login), **repositories** are the only code that queries tables.
- All errors use one JSON shape: `{"error": {"code", "message", "details"?}}`. Unexpected errors are logged server-side and never leak internals to the client.

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
    api/routes/      HTTP endpoints (auth, health)
    api/deps.py      shared dependencies (DB session, current user)
    core/            settings, security (hashing, tokens), error handling
    db/              engine, session, declarative base
    models/          SQLAlchemy models
    repositories/    database queries
    schemas/         Pydantic request/response models
    services/        business rules
  alembic/           migrations
  tests/
frontend/
  src/app/           pages (landing, login, register, dashboard)
  src/components/    UI primitives
  src/features/      feature modules (auth hooks and components)
  src/lib/api/       generated types + typed client
  src/proxy.ts       optimistic auth redirects
  e2e/               Playwright tests
docs/                spec, interview guide
```

## Roadmap

- [x] **Phase 1 · Foundation:** project setup, database and migrations, secure email/password auth, Arabic RTL interface, unit + integration + E2E tests, CI.
- [ ] **Phase 2 · Documents:** PDF upload and validation, background processing worker (Postgres job queue), Arabic-aware text extraction and chunking, embeddings stored in pgvector, document library with live processing status.
- [ ] **Phase 3 · Answers:** hybrid search (vector + keyword), question answering with validated page citations, source viewer that opens the cited page, conversation history, retrieval evaluation (Recall@K, MRR, refusal on unanswerable questions), deployment guide.

## Known limitations

- Phase 1 only: no documents or answers yet.
- Login has no rate limiting yet (planned alongside the AI endpoints in Phase 3).
- No email verification or password reset.
