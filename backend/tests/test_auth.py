from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import register_user

COOKIE = get_settings().auth_cookie_name


def test_register_creates_user_and_logs_in(client: TestClient):
    response = register_user(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jana@example.com"
    assert "password" not in body and "password_hash" not in body
    assert COOKIE in response.cookies

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]


def test_session_cookie_is_http_only(client: TestClient):
    response = register_user(client)
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_register_rejects_duplicate_email_case_insensitively(client: TestClient):
    register_user(client, email="jana@example.com")
    response = register_user(client, email="JANA@Example.com")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_register_validates_input(client: TestClient):
    response = client.post(
        "/api/v1/auth/register", json={"name": "L", "email": "not-an-email", "password": "short"}
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert {d["field"] for d in error["details"]} == {"name", "email", "password"}


def test_password_is_stored_hashed(client: TestClient):
    from sqlalchemy import text

    from app.db.session import engine

    register_user(client, password="s3cure-pass")
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users")).scalar_one()
    assert stored != "s3cure-pass"
    assert stored.startswith("$argon2")


def test_login_with_correct_password(client: TestClient):
    register_user(client)
    client.cookies.clear()

    response = client.post(
        "/api/v1/auth/login", json={"email": "Jana@example.com", "password": "s3cure-pass"}
    )

    assert response.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200


def test_login_errors_do_not_reveal_whether_email_exists(client: TestClient):
    register_user(client)
    client.cookies.clear()

    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "jana@example.com", "password": "wrong-pass"}
    )
    unknown_email = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-pass"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_login(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_rejects_tampered_token(client: TestClient):
    client.cookies.set(COOKIE, "not.a.valid.token")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_clears_session(client: TestClient):
    register_user(client)
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
