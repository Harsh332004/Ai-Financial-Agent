from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class ReportBase(BaseModel):
    run_id: uuid.UUID | None = Field(None, description="Agent run that generated this report")
    company_id: uuid.UUID | None = Field(None, description="Company this report is about")
    title: str = Field(..., description="Report title", example="Analysis: Apple Inc.")
    file_path: str = Field(..., description="Absolute path to the PDF file on disk")


class ReportCreate(ReportBase):
    pass


class ReportResponse(ReportBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Report unique identifier")
    created_by: uuid.UUID | None = Field(None, description="User who triggered the agent run")
    created_at: datetime = Field(..., description="Report creation timestamp (UTC)")
