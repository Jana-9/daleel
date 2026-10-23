# Progress

Updated at the end of every phase. Read with `docs/SPEC.md` before starting work.

## Phase 1 · Foundation: done (2026-10-23)

Built:
- Backend: FastAPI app, settings with production safety checks, consistent error shape, SQLAlchemy session, `users` table via Alembic (pgvector enabled), register / login / logout / me, health check with DB probe.
- Frontend: Next.js 16 + Tailwind 4, Arabic RTL design system (light and dark), landing, login, register, dashboard (empty state), typed API client generated from OpenAPI, React Query hooks, `proxy.ts` redirects.
- Tests: 15 backend tests (real Postgres, schema built from migrations); 10 Playwright E2E runs (5 scenarios × desktop and phone).
- CI: backend lint + tests + `alembic check` + OpenAPI drift; frontend types drift + lint + typecheck + build; E2E job.
- Docs: README, this file, spec, interview guide (Phase 1 section).

Verified locally: all backend tests, lint, format, `alembic check`, frontend lint, typecheck, production build, all E2E tests, WCAG AA contrast for every colour pair, no horizontal scroll at 390px.

Not verified yet: the GitHub Actions workflow has not run on GitHub (written and YAML-validated only). `docker compose up` was validated with `docker compose config` but not started.

## Phase 2 · Documents: next

Start with: migration for `documents`, `processing_jobs`, `document_chunks` → storage service → upload endpoint with validation → worker with SKIP LOCKED → extraction + normalisation + chunking (unit tests first) → embedding provider interface + fake → library UI.

Decision needed from Jana before embeddings: which AI provider/API key to use (or a free local embedding model).

## Phase 3 · Answers: later
