"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories import users as users_repo

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    """Resolve the logged-in user from the httpOnly session cookie, or reject with 401."""
    token = request.cookies.get(get_settings().auth_cookie_name)
    user_id = decode_access_token(token) if token else None
    user = users_repo.get_by_id(db, user_id) if user_id else None
    if user is None:
        raise AppError(401, "not_authenticated", "Please log in to continue.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
