"""Pydantic schemas for the v1 authentication boundary."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# bcrypt accepts at most 72 bytes; enforce it explicitly instead of
# silently truncating longer passwords.
PasswordStr = Field(min_length=8, max_length=72)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = PasswordStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = PasswordStr


class UserResponse(BaseModel):
    """Public user shape. Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    """Token/auth response returned by register and login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
