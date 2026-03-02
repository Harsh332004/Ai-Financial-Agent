from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class AlertBase(BaseModel):
    company_id: uuid.UUID | None = Field(None, description="Company this alert is about")
    run_id: uuid.UUID | None = Field(None, description="Agent run that created this alert")
    level: str = Field(
        ...,
        description="Severity level: `info` | `warning` | `critical`",
        example="warning",
    )
    message: str = Field(..., description="Human-readable alert message", example="Revenue declined >5% YoY")
    details: dict[str, Any] | None = Field(None, description="Structured data supporting the alert")
    acknowledged: bool = Field(False, description="Whether the alert has been reviewed")


class AlertCreate(AlertBase):
    company_id: uuid.UUID = Field(..., description="Company this alert is about (required on creation)")


class AlertAcknowledge(BaseModel):
    acknowledged: bool = Field(True, description="Set to true to mark the alert as reviewed")


class AlertResponse(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Alert unique identifier")
    acknowledged_by: uuid.UUID | None = Field(None, description="UUID of the user who acknowledged the alert")
    acknowledged_at: datetime | None = Field(None, description="When the alert was acknowledged (UTC)")
    created_at: datetime = Field(..., description="When the alert was raised (UTC)")
