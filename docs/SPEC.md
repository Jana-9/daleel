# Daleel: build spec

The single source of truth for what is being built. Read this together with `PROGRESS.md` before starting work on a phase.

## Product

A web app where a user uploads PDF documents (Arabic or English), asks questions in natural language, and gets answers grounded only in those documents, with the page number and passage for every claim. If the documents do not contain the answer, the app says so.

Target users: students and staff reading university regulations, employees reading company policies.

## Scope

**In:** email/password accounts, one private document space per user, PDF upload, background processing, Arabic-aware extraction, hybrid search, cited answers, a source viewer that opens the cited page, conversation history, an evaluation script, CI, a deployment guide.

**Out for now (possible v2):** shared workspaces and roles, DOCX, OCR for scanned PDFs, reranking models, analytics dashboard, OAuth, email verification, bilingual UI toggle.

## Architecture decisions (already made)

| Decision | Choice | Why |
| --- | --- | --- |
| API style | REST under `/api/v1`, OpenAPI as the contract | Typed frontend client is generated from it |
| Auth | Argon2id + JWT in `httpOnly`, `SameSite=Lax` cookie | Not readable by JS; basic CSRF protection |
| Frontend ↔ API | Next.js rewrites `/api/*` to FastAPI | Same origin, no CORS |
| DB access | SQLAlchemy 2 (sync) + repositories | Simple to reason about; FastAPI runs sync routes in a threadpool |
| Migrations | Alembic only, `alembic check` in CI | Schema never drifts from models |
| Errors | `{"error": {"code", "message", "details"?}}` | One shape for UI and tests |
| Background jobs | `processing_jobs` table + worker process using `SELECT ... FOR UPDATE SKIP LOCKED` | No Redis/Celery; survives restarts; safe with several workers |
| File storage | `StorageService` interface; local disk in dev, S3-compatible in prod; storage key = UUID, never the filename | Swappable, no path traversal |
| AI providers | `EmbeddingProvider` and `LLMProvider` interfaces, plus a deterministic fake for tests | Swap providers without touching the pipeline; tests never call paid APIs |
| Vector index | pgvector HNSW, cosine distance; store `embedding_model` with each chunk | Know what needs re-embedding after a model change |

## Phase 2: Documents

Tables: `documents` (id, owner_id, title, original_filename, storage_key, mime_type, file_size, page_count, status, error, timestamps), `processing_jobs` (id, document_id, status, attempts, locked_at, started_at, finished_at, error), `document_chunks` (id, document_id, chunk_index, page_number, content, content_normalized, embedding vector(N), embedding_model, token_count, char_start, char_end, bbox jsonb, created_at; unique (document_id, chunk_index)).

Statuses: `UPLOADED → PROCESSING → READY | FAILED`. Only READY after chunks and embeddings are committed.

Pipeline: validate (PDF magic bytes, size and page limits) → extract text per page with PyMuPDF (keep page numbers and word bounding boxes) → detect pages with almost no text (mark FAILED with a clear "scanned PDF not supported yet" message) → normalise Arabic for search (unify alef forms, remove tatweel and diacritics, NFKC) while keeping the original text for display → chunk per page with overlap → embed in batches → write chunks in one transaction (delete old chunks first, so retries are idempotent) → set READY.

Endpoints: `POST /api/v1/documents` (multipart), `GET /api/v1/documents`, `GET /api/v1/documents/{id}`, `GET /api/v1/documents/{id}/file`, `DELETE /api/v1/documents/{id}`, `POST /api/v1/documents/{id}/retry`. Every query filters by `owner_id`; another user's document returns 404 (not 403) so IDs do not leak.

UI: upload (drag and drop + picker, size/type checks), library list with status chips that poll while processing, delete, retry on failure.

Tests: normalisation and chunking units, upload validation, ownership isolation, worker claims a job once under concurrency, retry does not duplicate chunks, E2E upload → READY.

## Phase 3: Answers

Search: vector similarity (pgvector) + keyword (`pg_trgm` on normalised text, which works for Arabic) merged with Reciprocal Rank Fusion. Top-K configurable.

Answering: retrieve → build prompt with numbered passages, treating document text as untrusted data → model answers with inline markers `[1]`, `[2]` → backend keeps only markers that point to retrieved passages → if nothing relevant was retrieved, return a "not found in your documents" answer without calling the model. Stream with SSE.

Tables: `conversations`, `messages`, `message_sources` (message_id, chunk_id, rank, page_number, excerpt).

UI: chat page with streaming answer, numbered citation chips, source panel; clicking a citation opens the PDF at that page and highlights the passage (bbox). Conversation list, rename, delete.

Evaluation: `backend/eval/` with ~30 questions (Arabic and English, including unanswerable ones) over public sample documents; script reports Recall@5, MRR, citation validity, refusal accuracy, latency. Results go in the README with dataset size and limitations.

Delivery: rate limit on login and ask endpoints, Dockerfiles, deployment guide, README results, `docs/interview-guide.md` completed.
