from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class PasswordResetToken(Base):
    """
    Stores password-reset tokens as SHA-256 hashes.

    The raw token is NEVER persisted here — only its hash is stored.
    The raw token is sent to the user via email and validated by hashing
    the incoming value and comparing against token_hash.
    """
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True, default=None)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", backref="password_reset_tokens")
