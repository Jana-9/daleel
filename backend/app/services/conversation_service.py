"""Conversations: create, list, rename, delete, and ask a question inside one."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.conversation import Conversation, Message, MessageRole, MessageSource
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.repositories import conversations as conversations_repo
from app.repositories import documents as documents_repo
from app.schemas.conversations import AskResponse, ConversationOut, MessageOut
from app.services import rag_service
from app.services.llm import LLMError

logger = logging.getLogger(__name__)

DEFAULT_TITLE = "محادثة جديدة"

# Model failures, as (HTTP status, user-facing message). Details stay in the server log.
_LLM_ERRORS = {
    "llm_not_configured": (503, "Answering is not configured: GEMINI_API_KEY is missing."),
    "llm_auth": (503, "The AI provider rejected the API key."),
    "llm_model_not_found": (503, "The configured AI model is not available for this API key."),
    "llm_quota": (429, "The AI provider's usage limit was reached. Try again later."),
    "llm_unavailable": (503, "The AI provider did not respond. Try again."),
    "llm_bad_response": (502, "The AI provider returned an unusable answer. Try again."),
}


def _not_found() -> AppError:
    return AppError(404, "conversation_not_found", "Conversation not found.")


def get_conversation(db: Session, owner: User, conversation_id: uuid.UUID) -> Conversation:
    conversation = conversations_repo.get_owned(db, conversation_id, owner.id, with_messages=True)
    if conversation is None:
        raise _not_found()
    return conversation


def create(db: Session, owner: User, title: str | None) -> Conversation:
    conversation = Conversation(owner_id=owner.id, title=(title or "").strip() or DEFAULT_TITLE)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def rename(db: Session, owner: User, conversation_id: uuid.UUID, title: str) -> Conversation:
    conversation = get_conversation(db, owner, conversation_id)
    conversation.title = title
    db.commit()
    db.refresh(conversation)
    return conversation


def delete(db: Session, owner: User, conversation_id: uuid.UUID) -> None:
    db.delete(get_conversation(db, owner, conversation_id))
    db.commit()


def _check_rate_limit(db: Session, owner: User) -> None:
    settings = get_settings()
    limits = [
        (timedelta(minutes=1), settings.questions_per_minute),
        (timedelta(days=1), settings.questions_per_day),
    ]
    for window, limit in limits:
        if conversations_repo.questions_since(db, owner.id, window) >= limit:
            raise AppError(429, "rate_limited", "Too many questions. Please wait and try again.")


def _check_documents(db: Session, owner: User, document_id: uuid.UUID | None) -> None:
    if document_id is not None:
        document = documents_repo.get_owned(db, document_id, owner.id)
        if document is None:
            raise AppError(404, "document_not_found", "Document not found.")
        if document.status != DocumentStatus.READY:
            raise AppError(409, "document_not_ready", "This document is not ready yet.")
        return
    ready = db.scalar(
        select(func.count())
        .select_from(Document)
        .where(Document.owner_id == owner.id, Document.status == DocumentStatus.READY)
    )
    if not ready:
        raise AppError(409, "no_ready_documents", "Upload a document and wait until it is ready.")


def ask(
    db: Session,
    owner: User,
    conversation_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None,
) -> AskResponse:
    conversation = get_conversation(db, owner, conversation_id)
    _check_rate_limit(db, owner)
    _check_documents(db, owner, document_id)

    try:
        result = rag_service.answer_question(db, owner, question, document_id)
    except LLMError as exc:
        logger.warning("LLM failure %s: %s", exc.code, exc)
        status, message = _LLM_ERRORS.get(exc.code, (503, "The AI provider failed."))
        # Nothing is saved, so the user can simply ask again.
        raise AppError(status, exc.code, message) from exc

    # Question and answer are saved together, in one transaction.
    now = datetime.now(UTC)
    user_message = Message(
        conversation_id=conversation.id, role=MessageRole.USER, content=question, created_at=now
    )
    answer_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=result.content,
        status=result.status,
        model=result.model,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        # A microsecond later, so ordering by time always puts the answer after the question.
        created_at=now + timedelta(microseconds=1),
        sources=[
            MessageSource(
                marker=s.marker,
                document_id=s.hit.document_id,
                chunk_id=s.hit.chunk_id,
                document_title=s.hit.document_title,
                page_number=s.hit.page_number,
                excerpt=s.hit.content,
                bboxes=s.hit.bboxes,
            )
            for s in result.sources
        ],
    )
    db.add_all([user_message, answer_message])
    if conversation.title == DEFAULT_TITLE:
        conversation.title = question if len(question) <= 80 else question[:79].rstrip() + "…"
    conversation.updated_at = now
    db.commit()
    db.refresh(conversation)

    return AskResponse(
        conversation=ConversationOut.model_validate(conversation),
        question=MessageOut.model_validate(user_message),
        answer=MessageOut.model_validate(answer_message),
    )
