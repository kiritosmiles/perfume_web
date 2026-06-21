"""Pydantic models for auth endpoints."""

from pydantic import BaseModel, field_validator


class RegisterInput(BaseModel):
    email: str
    password: str
    browser_id: str | None = None

    @field_validator("email")
    @classmethod
    def email_has_at(cls, v: str) -> str:
        if "@" not in v or len(v.strip()) < 5:
            raise ValueError("Invalid email format")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginInput(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_has_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.strip().lower()


class RefreshInput(BaseModel):
    refresh_token: str
