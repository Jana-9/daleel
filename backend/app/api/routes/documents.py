import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.schemas.common import ErrorResponse
from app.schemas.documents import DocumentListOut, DocumentOut
from app.services import document_service
from app.services.storage_service import Storage, get_storage

router = APIRouter(prefix="/documents", tags=["documents"])
StorageDep = Annotated[Storage, Depends(get_storage)]
NOT_FOUND = {404: {"model": ErrorResponse}}


@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def upload_document(
    user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    file: Annotated[UploadFile, File(description="A PDF file")],
) -> DocumentOut:
    # A plain `def` (not async): parsing the PDF and writing to disk/DB are blocking, so FastAPI
    # runs this in a thread pool instead of freezing the event loop for every other request.
    # Read at most one byte over the limit: enough to know it is too big, without loading
    # an arbitrarily large upload into memory.
    data = file.file.read(get_settings().max_upload_bytes + 1)
    return document_service.upload(db, storage, user, file.filename, data)


@router.get("", response_model=DocumentListOut)
def list_documents(user: CurrentUser, db: DbSession) -> DocumentListOut:
    return DocumentListOut(items=document_service.list_documents(db, user))


@router.get("/{document_id}", response_model=DocumentOut, responses=NOT_FOUND)
def get_document(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> DocumentOut:
    return document_service.get_document_out(db, user, document_id)


@router.get(
    "/{document_id}/file",
    response_class=FileResponse,
    responses={**NOT_FOUND, 200: {"content": {"application/pdf": {}}}},
)
def download_file(
    document_id: uuid.UUID, user: CurrentUser, db: DbSession, storage: StorageDep
) -> FileResponse:
    document = document_service.get_document(db, user, document_id)
    return FileResponse(
        storage.path(document.storage_key),
        media_type="application/pdf",
        filename=document.original_filename,
        content_disposition_type="inline",  # open in the browser's viewer
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=0"},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_document(
    document_id: uuid.UUID, user: CurrentUser, db: DbSession, storage: StorageDep
) -> None:
    document_service.delete_document(db, storage, user, document_id)


@router.post(
    "/{document_id}/retry",
    response_model=DocumentOut,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse}},
)
def retry_document(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> DocumentOut:
    return document_service.retry_document(db, user, document_id)
