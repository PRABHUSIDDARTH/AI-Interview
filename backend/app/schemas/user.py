from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserUpdateMe(BaseModel):
    """Schema for self-service profile update (name + optional password change)."""
    full_name: Optional[str] = Field(None, max_length=100)
    current_password: Optional[str] = Field(None, description="Required when changing password")
    new_password: Optional[str] = Field(None, min_length=8, description="New password (min 8 chars)")

class UserInDBBase(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class User(UserInDBBase):
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None


# ---------------------------------------------------------------------------
# Password reset schemas
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Registered email address")

    @field_validator("email")
    @classmethod
    def email_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("email must not be empty")
        return v


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Raw reset token received via email")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")
