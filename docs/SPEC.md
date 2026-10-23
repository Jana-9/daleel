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
| Embedding model | `paraphrase-multilingual-MiniLM-L12-v2` via fastembed, 384 dims, CPU | Free, private, handles Arabic and cross-lingual queries; vector size fixed by migration 0002 |
| Chunk size | 450 characters, 90 overlap | Measured: model reads 128 tokens, ~3.9 Arabic chars/token; 900 chars was truncated |
| Worker placement | Thread inside the API in development; separate `app.worker` process in production | One command to run locally; independent scaling in production |
| Failure reporting | `documents.error_code` (stable code) + `processing_jobs.error_detail` (internal) | UI translates codes; internals never reach the client |

## Phase 2: Documents

**Status: done.** Tables as built: `documents` (id, owner_id, title, original_filename, storage_key, mime_type, file_size, page_count, status, error_code, processed_at, timestamps), `processing_jobs` (id, document_id, status, attempts, error_code, error_detail, locked_at, started_at, finished_at, duration_ms, created_at), `document_chunks` (id, document_id, chunk_index, page_number, content, content_normalized, word_count, bboxes jsonb, embedding vector(384), embedding_model, created_at; unique (document_id, chunk_index)).

Statuses: `UPLOADED → PROCESSING → READY | FAILED`. Only READY after chunks and embeddings are committed.

Pipeline: validate (PDF magic bytes, size and page limits) → extract text per page with PyMuPDF (keep page numbers and word bounding boxes) → detect pages with almost no text (mark FAILED with a clear "scanned PDF not supported yet" message) → normalise Arabic for search (unify alef forms, remove tatweel and diacritics, NFKC) while keeping the original text for display → chunk per page with overlap → embed in batches → write chunks in one transaction (delete old chunks first, so retries are idempotent) → set READY.

Endpoints: `POST /api/v1/documents` (multipart), `GET /api/v1/documents`, `GET /api/v1/documents/{id}`, `GET /api/v1/documents/{id}/file`, `DELETE /api/v1/documents/{id}`, `POST /api/v1/documents/{id}/retry`. Every query filters by `owner_id`; another user's document returns 404 (not 403) so IDs do not leak.

UI: upload (drag and drop + picker, size/type checks), library list with status chips that poll while processing, delete, retry on failure.

Tests: normalisation and chunking units, upload validation, ownership isolation, worker claims a job once under concurrency, retry does not duplicate chunks, E2E upload → READY.

## Phase 3: Answers

**Status: done**, with these deviations from the original plan (each for a stated reason):

| Planned | Built | Why |
| --- | --- | --- |
| Keyword search with `pg_trgm` | `LIKE` substring matching on normalised text, IDF-weighted, in SQL | `pg_trgm` and Postgres full-text search classify characters by database locale; with a `C` locale, Arabic letters are not treated as word characters. Substring matching works in any locale. No index: fine for one user's documents. |
| Plain RRF | RRF where keyword results must contain ≥60% of the question's keywords | Measured: plain RRF dropped Recall@1 from 90% (vector) to 70%; with the rule it is 95%. |
| Similarity threshold decides "not found" | Low floor (0.25) only skips obviously unrelated questions; the model decides, the backend verifies citations | Measured: unanswerable questions scored up to 0.67, answerable as low as 0.32. |
| Streaming answers (SSE) | Single JSON response | Kept the answer as validated JSON; Flash-Lite answers in a few seconds. Streaming is a later improvement. |
| Rate limit on login and ask | Ask only (per user, per minute and per day, counted from saved questions) | The ask endpoint costs API quota; login limiting is still open. |
| Dockerfiles + deployment guide | Not yet | Deferred until the GitHub repository exists; Docker could not be run in the build environment. |

Tables: `conversations` (owner, title), `messages` (role, content, status, model, latency, token counts), `message_sources` (marker, document/chunk ids with ON DELETE SET NULL, title, page, excerpt, bboxes).

Endpoints: `POST /api/v1/search`; `GET/POST /api/v1/conversations`; `GET/PATCH/DELETE /api/v1/conversations/{id}`; `POST /api/v1/conversations/{id}/messages`.

Answer model: Gemini via REST (`x-goog-api-key` header, so the newer "AQ." keys work), JSON output, temperature 0.1, configurable model (`gemini-3.5-flash-lite` default). `FakeLLMProvider` for tests and CI.

UI: `/chat` with conversation list, answer with citation chips and source list, side sheet with the pdf.js-rendered page and highlighted rectangles, rename/delete, example questions, "no ready documents" state.

Evaluation: `backend/eval/questions.json` (25 questions), `eval/run_eval.py` (Recall@1/3/5, MRR, latency, unanswerable similarity; `--answers` for grounding and refusal with the real model), results in `eval/results.md`.
