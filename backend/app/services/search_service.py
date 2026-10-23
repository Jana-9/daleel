"""Hybrid search over a user's documents: meaning (vectors) + words (keywords), fused by rank.

Why both:
- Vector search finds passages that mean the same thing in other words or another language
  ("كم رسوم السكن؟" finds "Housing fees of 1,500 riyals").
- Keyword search catches what a small embedding model misses, e.g. dialect questions that share
  key words with the rule ("نسبة الغياب ... الاختبار").

Reciprocal Rank Fusion combines the two lists using only positions (1/(k + rank)), so the
scores of the two methods never need to be on the same scale.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import Row, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from app.core.config import get_settings
from app.services.embeddings import EmbeddingProvider
from app.services.text_normalization import normalize_for_search

# Question words, dialect fillers and very common words carry no topic, so they are not keywords.
# Stored in normalized form (ة→ه, ى→ي, no hamza on alef).
STOPWORDS = {
    # Arabic (MSA and Gulf/Hijazi dialect)
    "ما", "ماذا", "متي", "اين", "كيف", "كم", "هل", "لماذا", "من", "مين", "وش", "ايش", "اش",
    "في", "علي", "عن", "الي", "او", "ثم", "مع", "هو", "هي", "هم", "انا", "انت", "انتي",
    "هذا", "هذه", "هذي", "ذلك", "تلك", "التي", "الذي", "اللي", "اذا", "لو", "كان", "يكون",
    "ابي", "ابغي", "ابغا", "ودي", "اقدر", "يقدر", "يمكن", "ممكن", "لازم", "يجب", "عشان",
    "شي", "شيء", "فيه", "فيها", "عندي", "عند", "بعد", "قبل", "كل", "اي", "غير", "بس", "لا",
    "نعم", "طيب", "يعني", "ايه", "اقول", "قول", "لي", "له", "لها",
    # English
    "a", "an", "the", "is", "are", "was", "were", "be", "do", "does", "did", "can", "could",
    "what", "when", "where", "which", "who", "why", "how", "much", "many", "i", "my", "me",
    "you", "your", "it", "its", "of", "to", "in", "on", "for", "at", "by", "and", "or", "if",
    "there", "this", "that", "with", "from", "about", "any", "happens",
}  # fmt: skip
_ARTICLE_PREFIXES = ("وال", "بال", "فال", "كال", "لل", "ال")


@dataclass
class SearchHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int
    content: str
    bboxes: list[list[float]]
    similarity: float = 0.0  # cosine similarity in [-1, 1]; 0 if not in the vector list
    vector_rank: int | None = None
    keyword_rank: int | None = None
    keyword_score: float = 0.0
    score: float = field(default=0.0)  # fused RRF score, used for the final order

    @property
    def keyword_matched(self) -> bool:
        return self.keyword_rank is not None


def keyword_terms(query: str) -> list[str]:
    """Distinct, normalized content words of a query, with the Arabic article removed.

    Matching is by substring, so "غياب" also finds "غيابه" and "الغياب".
    """
    terms: list[str] = []
    for word in normalize_for_search(query).split():
        if word in STOPWORDS:
            continue
        for prefix in _ARTICLE_PREFIXES:
            if word.startswith(prefix) and len(word) - len(prefix) >= 3:
                word = word[len(prefix) :]
                break
        long_enough = len(word) >= 3 or (word.isdigit() and len(word) >= 2)
        if long_enough and word not in terms:
            terms.append(word)
    return terms


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# Shared filter: only the owner's READY documents, only vectors made by the current model
# (vectors from different models are not comparable).
_SCOPE = """
    FROM document_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE d.owner_id = :owner_id
      AND d.status = 'ready'
      AND c.embedding_model = :model
      AND (CAST(:document_id AS uuid) IS NULL OR d.id = CAST(:document_id AS uuid))
"""

_VECTOR_SQL = text(f"""
    SELECT c.id, 1 - (c.embedding <=> CAST(:query_vector AS vector)) AS similarity
    {_SCOPE}
    ORDER BY c.embedding <=> CAST(:query_vector AS vector)
    LIMIT :limit
""")

# Each matched term adds its inverse document frequency (rarer words count more), computed
# over the same scope, so "تدريب" (in many passages) weighs less than "غياب" (in one).
_KEYWORD_SQL = text(f"""
    WITH scope AS (SELECT c.id, c.content_normalized {_SCOPE}),
    terms AS (SELECT unnest(CAST(:patterns AS text[])) AS pattern),
    df AS (
        SELECT t.pattern, count(s.id) AS df
        FROM terms t JOIN scope s ON s.content_normalized LIKE t.pattern ESCAPE '\\'
        GROUP BY t.pattern
    ),
    total AS (SELECT count(*) AS n FROM scope)
    SELECT s.id, sum(ln(1 + total.n::float / df.df)) AS score, count(*) AS matched
    FROM scope s
    JOIN df ON s.content_normalized LIKE df.pattern ESCAPE '\\'
    CROSS JOIN total
    GROUP BY s.id
    ORDER BY score DESC, s.id
    LIMIT :limit
""").bindparams(bindparam("patterns", type_=ARRAY(String)))

_DETAILS_SQL = text("""
    SELECT c.id, c.document_id, d.title, c.page_number, c.content, c.bboxes
    FROM document_chunks c JOIN documents d ON d.id = c.document_id
    WHERE c.id = ANY(:ids)
""")


def _vector_ranking(db: Session, params: dict, query_vector: list[float], limit: int) -> list[Row]:
    return list(
        db.execute(_VECTOR_SQL, {**params, "query_vector": str(query_vector), "limit": limit})
    )


def _keyword_ranking(db: Session, params: dict, terms: list[str], limit: int) -> list[Row]:
    if not terms:
        return []
    patterns = [_like_pattern(t) for t in terms]
    return list(db.execute(_KEYWORD_SQL, {**params, "patterns": patterns, "limit": limit}))


def search(
    db: Session,
    provider: EmbeddingProvider,
    owner_id: uuid.UUID,
    query: str,
    *,
    limit: int,
    document_id: uuid.UUID | None = None,
    mode: str = "hybrid",
) -> list[SearchHit]:
    """Best passages for `query` among the owner's ready documents. `mode` is "hybrid",
    "vector" or "keyword" (the last two exist for evaluation and comparison)."""
    settings = get_settings()
    params = {
        "owner_id": owner_id,
        "model": provider.model_name,
        "document_id": str(document_id) if document_id else None,
    }
    candidates = max(settings.search_candidates, limit)

    vector_rows = (
        _vector_ranking(db, params, provider.embed_query(query), candidates)
        if mode in ("hybrid", "vector")
        else []
    )
    terms = keyword_terms(query)
    keyword_rows = (
        _keyword_ranking(db, params, terms, candidates) if mode in ("hybrid", "keyword") else []
    )
    if mode == "hybrid":
        # Keep only passages that contain most of the question's keywords (see settings).
        needed = settings.keyword_min_coverage * len(terms)
        keyword_rows = [row for row in keyword_rows if row.matched >= needed]

    hits: dict[uuid.UUID, SearchHit] = {}

    def hit(chunk_id: uuid.UUID) -> SearchHit:
        if chunk_id not in hits:
            hits[chunk_id] = SearchHit(chunk_id, uuid.UUID(int=0), "", 0, "", [])
        return hits[chunk_id]

    for rank, (chunk_id, similarity) in enumerate(vector_rows, start=1):
        h = hit(chunk_id)
        h.vector_rank, h.similarity = rank, float(similarity)
        h.score += 1 / (settings.rrf_k + rank)
    for rank, row in enumerate(keyword_rows, start=1):
        h = hit(row.id)
        h.keyword_rank, h.keyword_score = rank, float(row.score)
        h.score += 1 / (settings.rrf_k + rank)

    best = sorted(hits.values(), key=lambda h: (-h.score, h.vector_rank or 10**6))[:limit]
    if not best:
        return []

    details = {row.id: row for row in db.execute(_DETAILS_SQL, {"ids": [h.chunk_id for h in best]})}
    for h in best:
        row = details[h.chunk_id]
        h.document_id, h.document_title = row.document_id, row.title
        h.page_number, h.content, h.bboxes = row.page_number, row.content, row.bboxes
    return best
