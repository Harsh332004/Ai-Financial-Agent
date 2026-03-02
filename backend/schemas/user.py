from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from pydantic.config import ConfigDict


class UserBase(BaseModel):
    email: str = Field(..., description="User's email address", example="analyst@example.com")
    full_name: str | None = Field(None, description="Display name", example="Jane Smith")
    role: str = Field("analyst", description="User role: `analyst` | `manager` | `admin`")
    is_active: bool = Field(True, description="Whether the account is active")


class UserCreate(BaseModel):
    email: str = Field(..., description="Email address (must be unique)", example="analyst@example.com")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)", example="SecurePass123!")
    full_name: str | None = Field(None, description="Optional display name", example="Jane Smith")


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, description="New display name")
    role: str | None = Field(None, description="New role: `analyst` | `manager` | `admin`")
    is_active: bool | None = Field(None, description="Activate or deactivate the account")


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="User's unique identifier (UUID)")
    created_at: datetime = Field(..., description="Account creation timestamp (UTC)")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer token — paste this into the Authorize 🔒 dialog")
    token_type: str = Field("bearer", description="Always `bearer`")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Registered email address", example="analyst@example.com")
    password: str = Field(..., description="Account password", example="SecurePass123!")
