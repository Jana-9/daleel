"""Data access for conversations and messages. Every user-facing read is scoped by owner."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, Message, MessageRole


def get_owned(
    db: Session, conversation_id: uuid.UUID, owner_id: uuid.UUID, *, with_messages: bool = False
) -> Conversation | None:
    query = select(Conversation).where(
        Conversation.id == conversation_id, Conversation.owner_id == owner_id
    )
    if with_messages:
        query = query.options(selectinload(Conversation.messages).selectinload(Message.sources))
    return db.scalar(query)


def list_owned(db: Session, owner_id: uuid.UUID) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.owner_id == owner_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id)
        )
    )


def questions_since(db: Session, owner_id: uuid.UUID, window: timedelta) -> int:
    """How many questions the user asked in the last `window` (for rate limiting)."""
    since = datetime.now(UTC) - window
    return db.scalar(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.owner_id == owner_id,
            Message.role == MessageRole.USER,
            Message.created_at >= since,
        )
    )
