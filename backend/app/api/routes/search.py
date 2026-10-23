from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.conversations import SearchHitOut, SearchOut, SearchRequest
from app.services import search_service
from app.services.embeddings import get_embedding_provider

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchOut)
def search(data: SearchRequest, user: CurrentUser, db: DbSession) -> SearchOut:
    """Hybrid (meaning + keyword) search across the user's ready documents. No AI model call."""
    hits = search_service.search(
        db,
        get_embedding_provider(),
        user.id,
        data.query,
        limit=data.limit,
        document_id=data.document_id,
    )
    return SearchOut(
        items=[
            SearchHitOut(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                document_title=h.document_title,
                page_number=h.page_number,
                excerpt=h.content,
                similarity=round(h.similarity, 4),
                keyword_matched=h.keyword_matched,
            )
            for h in hits
        ]
    )
