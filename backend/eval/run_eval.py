"""Measure retrieval quality on the sample guide with the real embedding model.

    uv run python -m eval.run_eval              # retrieval only (free, runs offline)
    uv run python -m eval.run_eval --answers    # also asks Gemini (needs GEMINI_API_KEY)

Uses the database in DATABASE_URL: it creates a temporary user, processes the sample PDF,
runs every question, then deletes the user (and with it, everything it created).
Results are printed and written to eval/results.md.
"""

import argparse
import json
import statistics
import time
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import User
from app.repositories import users as users_repo
from app.services import document_service, processing, search_service
from app.services.embeddings import get_embedding_provider
from app.services.storage_service import get_storage
from app.services.text_normalization import normalize_for_search

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
MODES = ("vector", "keyword", "hybrid")
KS = (1, 3, 5)


def first_correct_rank(hits, evidence: str) -> int | None:
    wanted = normalize_for_search(evidence)
    for rank, hit in enumerate(hits, start=1):
        if wanted in normalize_for_search(hit.content):
            return rank
    return None


def setup_user_with_sample(data: dict) -> uuid.UUID:
    with SessionLocal() as db:
        user = users_repo.create(
            db, name="eval", email=f"eval-{uuid.uuid4().hex}@example.com", password_hash="x"
        )
        db.commit()
        pdf = (ROOT / data["document"]).read_bytes()
        document = document_service.upload(db, get_storage(), user, "sample.pdf", pdf)
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        processing.process_next_job()  # also fine if a running API worker takes it
        with SessionLocal() as db:
            status = document_service.get_document(db, user, document.id).status
        if status in ("ready", "failed"):
            break
        time.sleep(0.5)
    if status != "ready":
        raise SystemExit(f"Sample document did not process: {status}")
    return user.id


def evaluate_retrieval(user_id: uuid.UUID, questions: list[dict]) -> dict:
    provider = get_embedding_provider()
    answerable = [q for q in questions if q["evidence"]]
    unanswerable = [q for q in questions if not q["evidence"]]
    results: dict = {"modes": {}, "per_question": {}, "unanswerable": []}

    with SessionLocal() as db:
        for mode in MODES:
            ranks, latencies = [], []
            for q in answerable:
                start = time.perf_counter()
                hits = search_service.search(
                    db, provider, user_id, q["question"], limit=max(KS), mode=mode
                )
                latencies.append((time.perf_counter() - start) * 1000)
                rank = first_correct_rank(hits, q["evidence"])
                ranks.append(rank)
                results["per_question"].setdefault(q["id"], {})[mode] = rank
            n = len(answerable)
            results["modes"][mode] = {
                **{f"recall@{k}": sum(1 for r in ranks if r and r <= k) / n for k in KS},
                "mrr": sum(1 / r for r in ranks if r) / n,
                "p50_ms": statistics.median(latencies),
            }
        for q in unanswerable:
            hits = search_service.search(db, provider, user_id, q["question"], limit=max(KS))
            results["unanswerable"].append(
                {
                    "id": q["id"],
                    "max_similarity": max((h.similarity for h in hits), default=0.0),
                    "keyword_match": any(h.keyword_matched for h in hits),
                }
            )
        results["answerable_top_similarity"] = [
            max(
                (
                    h.similarity
                    for h in search_service.search(db, provider, user_id, q["question"], limit=5)
                ),
                default=0.0,
            )
            for q in answerable
        ]
    return results


def evaluate_answers(user_id: uuid.UUID, questions: list[dict]) -> dict:
    """Full pipeline with the real LLM: is the answer grounded, and does it refuse correctly?"""
    from app.services import rag_service

    rows = []
    with SessionLocal() as db:
        user = db.get(User, user_id)
        for q in questions:
            start = time.perf_counter()
            result = rag_service.answer_question(db, user, q["question"])
            elapsed = (time.perf_counter() - start) * 1000
            cites_evidence = q["evidence"] is not None and any(
                normalize_for_search(q["evidence"]) in normalize_for_search(s.excerpt)
                for s in result.sources
            )
            rows.append(
                {
                    "id": q["id"],
                    "answerable": q["evidence"] is not None,
                    "status": result.status,
                    "cites_evidence": cites_evidence,
                    "ms": elapsed,
                }
            )
            time.sleep(4)  # stay well under free-tier per-minute limits
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    return {
        "answered_with_correct_source": sum(r["cites_evidence"] for r in answerable)
        / len(answerable),
        "wrongly_refused": sum(r["status"] == "not_found" for r in answerable) / len(answerable),
        "correctly_refused": sum(r["status"] == "not_found" for r in unanswerable)
        / len(unanswerable),
        "p50_ms": statistics.median(r["ms"] for r in rows),
        "rows": rows,
    }


def cleanup(user_id: uuid.UUID) -> None:
    storage = get_storage()
    with SessionLocal() as db:
        user = db.get(User, user_id)
        for document in document_service.list_documents(db, user):
            document_service.delete_document(db, storage, user, document.id)
        db.delete(db.get(User, user_id))
        db.commit()


def to_markdown(data: dict, retrieval: dict, answers: dict | None) -> str:
    settings = get_settings()
    answerable = [q for q in data["questions"] if q["evidence"]]
    lines = [
        "# Retrieval evaluation",
        "",
        f"Document: `{data['document']}` (4 pages, fictional). "
        f"{len(answerable)} answerable questions "
        f"({', '.join(sorted({q['kind'] for q in answerable}))}), "
        f"{len(data['questions']) - len(answerable)} unanswerable.",
        f"Embedding model: `{settings.embedding_model}`; chunks of {settings.chunk_size} "
        f"characters; RRF k = {settings.rrf_k}; hybrid keeps keyword results covering "
        f"≥ {settings.keyword_min_coverage:.0%} of the question's keywords.",
        "",
        "| Method | Recall@1 | Recall@3 | Recall@5 | MRR | Median latency |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for mode, m in retrieval["modes"].items():
        lines.append(
            f"| {mode} | {m['recall@1']:.0%} | {m['recall@3']:.0%} | {m['recall@5']:.0%} "
            f"| {m['mrr']:.2f} | {m['p50_ms']:.0f} ms |"
        )
    lines += ["", "Rank of the first correct passage per question (— = not in top 5):", ""]
    lines += ["| Question | Kind | " + " | ".join(MODES) + " |", "| --- | --- |" + " --- |" * 3]
    for q in answerable:
        ranks = retrieval["per_question"][q["id"]]
        cells = " | ".join(str(ranks[m]) if ranks[m] else "—" for m in MODES)
        lines.append(f"| {q['question']} | {q['kind']} | {cells} |")
    unans = retrieval["unanswerable"]
    lines += [
        "",
        "Unanswerable questions (best vector similarity, any keyword match):",
        "",
        *[
            f"- `{u['id']}`: {u['max_similarity']:.2f}, keyword match: {u['keyword_match']}"
            for u in unans
        ],
        f"- Lowest best-similarity among answerable questions: "
        f"{min(retrieval['answerable_top_similarity']):.2f}",
    ]
    if answers:
        lines += [
            "",
            f"## Answers ({settings.gemini_model})",
            "",
            "- Answered and cited the correct passage: "
            f"{answers['answered_with_correct_source']:.0%}",
            f"- Answerable but refused: {answers['wrongly_refused']:.0%}",
            f"- Unanswerable and correctly refused: {answers['correctly_refused']:.0%}",
            f"- Median time per answer: {answers['p50_ms']:.0f} ms",
        ]
    lines += [
        "",
        "Limitations: one short document (8 passages) and a small hand-written question set, "
        "so these numbers show relative differences between methods, not expected accuracy on "
        "real documents. With only 8 passages, Recall@5 is close to trivial; Recall@1 and MRR "
        "are the informative columns. The coverage threshold was chosen on this same set "
        "(results were identical at 60% and 75%), so a larger held-out set is needed to "
        "confirm it.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", action="store_true", help="also evaluate answers (uses LLM)")
    args = parser.parse_args()

    data = json.loads((EVAL_DIR / "questions.json").read_text(encoding="utf-8"))
    user_id = setup_user_with_sample(data)
    try:
        retrieval = evaluate_retrieval(user_id, data["questions"])
        answers = evaluate_answers(user_id, data["questions"]) if args.answers else None
    finally:
        cleanup(user_id)

    report = to_markdown(data, retrieval, answers)
    (EVAL_DIR / "results.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
