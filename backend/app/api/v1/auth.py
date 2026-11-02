import threading
import time
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User as UserModel
from app.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    User,
    UserCreate,
    UserUpdateMe,
)
from app.services import auth as auth_service
from app.services.email import send_password_reset_email

router = APIRouter()

# ---------------------------------------------------------------------------
# Simple in-memory rate-limit for forgot-password (per-email, 60-second cooldown)
# This is process-scoped and sufficient for single-instance MVP deployments.
# ---------------------------------------------------------------------------
_reset_cooldown: dict[str, float] = {}
_cooldown_lock = threading.Lock()
_FORGOT_PASSWORD_COOLDOWN_SECONDS = 60


def _is_rate_limited(email: str) -> bool:
    """Return True if this email made a request within the cooldown window."""
    with _cooldown_lock:
        last = _reset_cooldown.get(email)
        now = time.monotonic()
        if last is not None and (now - last) < _FORGOT_PASSWORD_COOLDOWN_SECONDS:
            return True
        _reset_cooldown[email] = now
        return False


# ---------------------------------------------------------------------------
# Existing endpoints (unchanged)
# ---------------------------------------------------------------------------

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(deps.get_db)) -> Any:
    """
    Register a new user.
    """
    user = auth_service.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    return auth_service.create_user(db, user_in=user_in)


@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = auth_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/me", response_model=User)
def read_user_me(
    current_user: UserModel = Depends(deps.get_current_user)
) -> Any:
    """
    Get profile of current logged in user.
    """
    return current_user


@router.put("/me", response_model=User)
def update_user_me(
    update_in: UserUpdateMe,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """
    Update profile of current logged in user (full_name and/or password).
    Changing password requires current_password for verification.
    """
    updated_user, error = auth_service.update_user_me(db, current_user, update_in)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return updated_user


# ---------------------------------------------------------------------------
# New password-reset endpoints
# ---------------------------------------------------------------------------

_GENERIC_RESET_MESSAGE = (
    "If an account with that email exists, password reset instructions have been sent."
)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(deps.get_db),
) -> dict:
    """
    Request a password-reset email.

    SECURITY:
    - Always returns the same generic message whether the email exists or not
      (prevents account/email enumeration).
    - Rate-limited to one request per email per 60 seconds.
    - Raw token is NEVER stored — only its SHA-256 hash.
    """
    email = body.email.strip().lower()

    # Rate-limit check (applied before user lookup to prevent timing attacks)
    if _is_rate_limited(email):
        # Return the same message — do not reveal rate-limiting to the caller
        return {"message": _GENERIC_RESET_MESSAGE}

    user = auth_service.get_user_by_email(db, email=email)
    if user and user.is_active:
        raw_token = auth_service.create_password_reset_token(
            db,
            user_id=user.id,
            expire_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )
        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        )
        # Fire-and-forget: SMTP errors are caught inside send_password_reset_email
        send_password_reset_email(
            to_email=user.email,
            reset_url=reset_url,
            expires_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )

    return {"message": _GENERIC_RESET_MESSAGE}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(deps.get_db),
) -> dict:
    """
    Reset a user's password using a single-use token.

    SECURITY:
    - Token is hashed before lookup — raw token never compared directly.
    - Expired tokens are rejected.
    - Already-used tokens are rejected.
    - Password is hashed with bcrypt before storage.
    - Token is marked used atomically with the password update.
    """
    token_record = auth_service.get_valid_reset_token(db, raw_token=body.token)
    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has expired.",
        )

    auth_service.consume_reset_token(db, token_record, new_password=body.new_password)
    return {"message": "Password reset successfully. You can now sign in with your new password."}
