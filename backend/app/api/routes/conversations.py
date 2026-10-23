import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.repositories import conversations as conversations_repo
from app.schemas.common import ErrorResponse
from app.schemas.conversations import (
    AskRequest,
    AskResponse,
    ConversationCreate,
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    ConversationUpdate,
)
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])
NOT_FOUND = {404: {"model": ErrorResponse}}


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationCreate, user: CurrentUser, db: DbSession
) -> ConversationOut:
    return ConversationOut.model_validate(conversation_service.create(db, user, data.title))


@router.get("", response_model=ConversationListOut)
def list_conversations(user: CurrentUser, db: DbSession) -> ConversationListOut:
    items = conversations_repo.list_owned(db, user.id)
    return ConversationListOut(items=[ConversationOut.model_validate(c) for c in items])


@router.get("/{conversation_id}", response_model=ConversationDetailOut, responses=NOT_FOUND)
def get_conversation(
    conversation_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> ConversationDetailOut:
    conversation = conversation_service.get_conversation(db, user, conversation_id)
    return ConversationDetailOut.model_validate(conversation, from_attributes=True)


@router.patch("/{conversation_id}", response_model=ConversationOut, responses=NOT_FOUND)
def rename_conversation(
    conversation_id: uuid.UUID, data: ConversationUpdate, user: CurrentUser, db: DbSession
) -> ConversationOut:
    conversation = conversation_service.rename(db, user, conversation_id, data.title)
    return ConversationOut.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_conversation(conversation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    conversation_service.delete(db, user, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=AskResponse,
    responses={
        **NOT_FOUND,
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def ask_question(
    conversation_id: uuid.UUID, data: AskRequest, user: CurrentUser, db: DbSession
) -> AskResponse:
    """Answer a question from the user's documents, with citations. Takes a few seconds."""
    return conversation_service.ask(db, user, conversation_id, data.question, data.document_id)
