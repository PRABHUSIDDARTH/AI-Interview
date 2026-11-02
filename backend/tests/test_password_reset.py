"""
Tests for forgot-password / reset-password flow.

Uses a single shared SQLite connection per test to avoid the `:memory:`
isolation issue (each SQLite :memory: connection gets its own database).

Tests:
  1. Forgot password with existing email → 200, generic message, token created
  2. Forgot password with unknown email → 200, same generic message (no enumeration)
  3. Reset using valid token → 200, password updated
  4. Reset using invalid token → 400 error
  5. Reset using expired token → 400 error
  6. Reset using already-used token → 400 error
  7. Password hash is changed after successful reset
  8. Old password no longer works after reset
  9. New password works after reset
 10. Existing login flow still works (regression)
"""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session as SASession

# Import app and its Base FIRST so the module-level create_all has run.
from app.main import app
from app.api import deps
from app.core.database import Base
from app.models import PasswordResetToken, User  # noqa: F401 — registers tables
from app.core.security import get_password_hash
from app.services.auth import create_password_reset_token


# ---------------------------------------------------------------------------
# Shared-connection SQLite fixture
# A single connection is used for the entire test so that tables created via
# create_all on that connection are visible to the session that runs queries.
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_client():
    """
    Yields (db_session, test_client).

    One SQLite :memory: database connection is shared between:
      - the SQLAlchemy Session (used by tests and service-layer helpers)
      - the FastAPI dependency override (used by HTTP endpoint handlers)
    This ensures create_all, direct inserts, and endpoint queries all operate
    on the same in-memory database.
    """
    # Create an engine that keeps a single connection alive for the test
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    connection = engine.connect()

    # Ensure the session always reuses this exact connection
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )

    # Create all tables on this connection
    Base.metadata.create_all(bind=connection)

    db = TestingSessionLocal()

    def override_get_db():
        yield db

    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as client:
        yield db, client

    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=connection)
    connection.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_EMAIL = "test@example.com"
_TEST_PASSWORD = "OldPassword123"
_NEW_PASSWORD = "NewSecurePassword456"


def _create_test_user(db, email=_TEST_EMAIL, password=_TEST_PASSWORD):
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name="Test User",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _sha256(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# 1. Forgot password with existing email
# ---------------------------------------------------------------------------

def test_forgot_password_existing_email(db_client):
    """Returns 200 with generic message; a reset token is created in the DB."""
    db, client = db_client
    _create_test_user(db)
    response = client.post("/api/v1/auth/forgot-password", json={"email": _TEST_EMAIL})
    assert response.status_code == 200
    assert "message" in response.json()
    token = db.query(PasswordResetToken).first()
    assert token is not None
    assert token.used_at is None


# ---------------------------------------------------------------------------
# 2. Forgot password with unknown email (no enumeration)
# ---------------------------------------------------------------------------

def test_forgot_password_unknown_email(db_client):
    """Returns 200 with SAME generic message even when email doesn't exist."""
    db, client = db_client
    response = client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert response.status_code == 200
    assert "message" in response.json()
    assert db.query(PasswordResetToken).count() == 0


# ---------------------------------------------------------------------------
# 3. Reset using valid token
# ---------------------------------------------------------------------------

def test_reset_with_valid_token(db_client):
    """Valid token + new password → 200, success message."""
    db, client = db_client
    user = _create_test_user(db)
    raw_token = create_password_reset_token(db, user_id=user.id, expire_minutes=30)

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": _NEW_PASSWORD},
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()


# ---------------------------------------------------------------------------
# 4. Reset using invalid token
# ---------------------------------------------------------------------------

def test_reset_with_invalid_token(db_client):
    """Completely bogus token string → 400."""
    db, client = db_client
    _create_test_user(db)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "totally-bogus-token", "new_password": _NEW_PASSWORD},
    )
    assert response.status_code == 400
    assert "invalid or has expired" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 5. Reset using expired token
# ---------------------------------------------------------------------------

def test_reset_with_expired_token(db_client):
    """Token whose expires_at is in the past → 400."""
    db, client = db_client
    user = _create_test_user(db)
    raw_token = "expired_raw_token_abc123xyz"
    expired_record = PasswordResetToken(
        user_id=user.id,
        token_hash=_sha256(raw_token),
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    db.add(expired_record)
    db.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": _NEW_PASSWORD},
    )
    assert response.status_code == 400
    assert "invalid or has expired" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. Reset using already-used token
# ---------------------------------------------------------------------------

def test_reset_with_already_used_token(db_client):
    """Token that has already been consumed → 400 on second use."""
    db, client = db_client
    user = _create_test_user(db)
    raw_token = create_password_reset_token(db, user_id=user.id, expire_minutes=30)

    r1 = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": _NEW_PASSWORD},
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "AnotherPassword789"},
    )
    assert r2.status_code == 400
    assert "invalid or has expired" in r2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 7. Password hash is changed after successful reset
# ---------------------------------------------------------------------------

def test_password_hash_changes_after_reset(db_client):
    """The stored hashed_password on the user record must change."""
    db, client = db_client
    user = _create_test_user(db)
    old_hash = user.hashed_password

    raw_token = create_password_reset_token(db, user_id=user.id, expire_minutes=30)
    client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": _NEW_PASSWORD},
    )

    db.refresh(user)
    assert user.hashed_password != old_hash


# ---------------------------------------------------------------------------
# 8. Old password no longer works after reset
# ---------------------------------------------------------------------------

def test_old_password_rejected_after_reset(db_client):
    """Login with old password must fail after reset."""
    db, client = db_client
    user = _create_test_user(db)
    raw_token = create_password_reset_token(db, user_id=user.id, expire_minutes=30)
    client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": _NEW_PASSWORD},
    )

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": _TEST_EMAIL, "password": _TEST_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 9. New password works after reset
# ---------------------------------------------------------------------------

def test_new_password_works_after_reset(db_client):
    """Login with new password must succeed after reset."""
    db, client = db_client
    user = _create_test_user(db)
    raw_token = create_password_reset_token(db, user_id=user.id, expire_minutes=30)
    client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": _NEW_PASSWORD},
    )

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": _TEST_EMAIL, "password": _NEW_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ---------------------------------------------------------------------------
# 10. Existing login flow still works (regression)
# ---------------------------------------------------------------------------

def test_existing_login_flow_regression(db_client):
    """Register → login → /me all work correctly (no regressions)."""
    db, client = db_client

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass999",
            "full_name": "New User",
        },
    )
    assert reg.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "newuser@example.com", "password": "SecurePass999"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "newuser@example.com"
