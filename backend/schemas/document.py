from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class DocumentBase(BaseModel):
    company_id: uuid.UUID | None = Field(None, description="UUID of the associated company")
    filename: str = Field(..., description="Stored filename (UUID-prefixed)")
    original_filename: str = Field(..., description="Original filename as uploaded by the user")
    doc_type: str | None = Field(
        None,
        description="Document category: `annual_report` | `earnings` | `balance_sheet` | `news` | `other`",
        example="annual_report",
    )
    file_path: str = Field(..., description="Absolute path to the file on disk")
    ocr_text: str | None = Field(None, description="Full extracted text (available after status=ready)")
    page_count: int = Field(1, description="Number of pages detected")
    status: str = Field(
        "processing",
        description="Processing status: `processing` → `ready` | `failed`",
    )
    uploaded_by: uuid.UUID | None = Field(None, description="UUID of the user who uploaded this document")


class DocumentCreate(BaseModel):
    company_id: uuid.UUID = Field(..., description="Company this document belongs to")
    doc_type: str | None = Field(None, description="Optional document category")


class DocumentUpdate(BaseModel):
    doc_type: str | None = Field(None, description="Updated document category")
    ocr_text: str | None = Field(None, description="Extracted OCR text (set by background worker)")
    page_count: int | None = Field(None, description="Updated page count")
    status: str | None = Field(None, description="Updated status: processing | ready | failed")


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Document's unique identifier (UUID)")
    uploaded_at: datetime = Field(..., description="Upload timestamp (UTC)")
