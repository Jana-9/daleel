from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut
from app.schemas.common import ErrorResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, user_id) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(user_id),
        max_age=settings.access_token_minutes * 60,
        httponly=True,  # JavaScript cannot read it, so XSS cannot steal the session
        secure=settings.cookie_secure,
        samesite="lax",  # not sent on cross-site POSTs, which blocks basic CSRF
        path="/",
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def register(data: RegisterRequest, response: Response, db: DbSession) -> UserOut:
    user = auth_service.register(db, data)
    _set_session_cookie(response, user.id)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut, responses={401: {"model": ErrorResponse}})
def login(data: LoginRequest, response: Response, db: DbSession) -> UserOut:
    user = auth_service.authenticate(db, data)
    _set_session_cookie(response, user.id)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(get_settings().auth_cookie_name, path="/")


@router.get("/me", response_model=UserOut, responses={401: {"model": ErrorResponse}})
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
