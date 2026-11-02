import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdateMe


# ---------------------------------------------------------------------------
# Existing auth helpers (unchanged)
# ---------------------------------------------------------------------------

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    if not email:
        return None
    cleaned_email = email.strip()
    return db.query(User).filter(func.lower(User.email) == cleaned_email.lower()).first()


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    if not email or not password:
        return None
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, user_in: UserCreate) -> User:
    cleaned_email = user_in.email.strip().lower()
    db_user = User(
        email=cleaned_email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name.strip() if user_in.full_name else None,
        is_active=user_in.is_active,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_me(db: Session, user: User, update_in: UserUpdateMe) -> Tuple[User, Optional[str]]:
    """Update the current user's full_name and/or password.

    Returns (updated_user, error_message). error_message is None on success.
    """
    # Handle password change
    if update_in.new_password is not None:
        if not update_in.current_password:
            return user, "current_password is required to set a new password."
        if not verify_password(update_in.current_password, user.hashed_password):
            return user, "Current password is incorrect."
        user.hashed_password = get_password_hash(update_in.new_password)

    # Handle name update (allow clearing to None)
    if update_in.full_name is not None:
        user.full_name = update_in.full_name.strip() or None

    db.add(user)
    db.commit()
    db.refresh(user)
    return user, None


# ---------------------------------------------------------------------------
# Password reset token helpers
# ---------------------------------------------------------------------------

def _hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of the raw token."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_password_reset_token(
    db: Session,
    user_id: int,
    expire_minutes: int = 30,
) -> str:
    """
    Generate a cryptographically secure random token, store only its hash,
    and return the raw token (to be sent to the user via email).

    Previous unused tokens for this user are left as-is; only the hash of
    the NEW token can validate a reset request.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

    reset_token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)

    return raw_token  # returned so the caller can embed it in the email URL


def get_valid_reset_token(
    db: Session, raw_token: str
) -> Optional[PasswordResetToken]:
    """
    Hash the supplied raw token, look it up, and return the record ONLY if:
      - It exists
      - It has not been used (used_at IS NULL)
      - It has not expired

    Returns None for any invalid / expired / already-used token.
    """
    token_hash = _hash_token(raw_token)
    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if record is None:
        return None
    if record.used_at is not None:
        return None
    now = datetime.now(timezone.utc)
    # expires_at may be naive (SQLite) — normalise
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        return None
    return record


def consume_reset_token(
    db: Session,
    token_record: PasswordResetToken,
    new_password: str,
) -> User:
    """
    Atomically:
      1. Hash and store the new password on the user record.
      2. Mark the reset token as used (single-use enforcement).
    """
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if user is None:
        raise ValueError("User associated with reset token not found.")

    user.hashed_password = get_password_hash(new_password)
    token_record.used_at = datetime.now(timezone.utc)

    db.add(user)
    db.add(token_record)
    db.commit()
    db.refresh(user)
    return user
