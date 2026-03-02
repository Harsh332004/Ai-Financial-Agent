from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class CompanyBase(BaseModel):
    name: str = Field(..., description="Company display name", example="Apple Inc.")
    ticker: str | None = Field(None, description="Stock ticker symbol", example="AAPL")
    sector: str | None = Field(None, description="Industry sector", example="Technology")
    exchange: str | None = Field(None, description="Stock exchange: NYSE | NASDAQ | NSE | BSE", example="NASDAQ")
    description: str | None = Field(None, description="Short description of the company")


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(None, description="Updated company name")
    ticker: str | None = Field(None, description="Updated ticker symbol")
    sector: str | None = Field(None, description="Updated sector")
    exchange: str | None = Field(None, description="Updated exchange")
    description: str | None = Field(None, description="Updated description")


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Company's unique identifier (UUID)")
    created_by: uuid.UUID | None = Field(None, description="UUID of the user who created this company")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
