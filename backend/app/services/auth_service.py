"""Registration and login rules. Routes stay thin; the decisions live here."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories import users as users_repo
from app.schemas.auth import LoginRequest, RegisterRequest

# A real hash computed once, so failed logins for unknown emails take the same time as
# failed logins for known emails. Otherwise response timing would reveal which emails exist.
_DUMMY_HASH = hash_password("timing-equalizer-password")


def register(db: Session, data: RegisterRequest) -> User:
    if users_repo.get_by_email(db, data.email):
        raise AppError(409, "email_taken", "An account with this email already exists.")
    try:
        user = users_repo.create(
            db, name=data.name, email=data.email, password_hash=hash_password(data.password)
        )
        db.commit()
    except IntegrityError as exc:
        # Two simultaneous sign-ups with the same email: the unique constraint decides.
        db.rollback()
        raise AppError(409, "email_taken", "An account with this email already exists.") from exc
    return user


def authenticate(db: Session, data: LoginRequest) -> User:
    user = users_repo.get_by_email(db, data.email)
    password_ok = verify_password(data.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not password_ok:
        # Same message for "no such email" and "wrong password".
        raise AppError(401, "invalid_credentials", "Incorrect email or password.")
    return user
