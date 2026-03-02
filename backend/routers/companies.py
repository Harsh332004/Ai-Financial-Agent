from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.company import Company
from backend.models.user import User
from backend.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from backend.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=list[CompanyResponse],
    summary="List all companies",
    description="Returns all companies sorted by creation date (newest first). Requires authentication.",
    response_description="Array of company objects",
)
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Company]:
    result = await db.execute(select(Company).order_by(Company.created_at.desc()))
    return list(result.scalars().all())


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new company",
    description=(
        "Add a company to track. Only `name` is required.\n\n"
        "- `ticker`: Stock ticker symbol (e.g. `AAPL`, `MSFT`, `RELIANCE.NS`)\n"
        "- `exchange`: `NYSE` | `NASDAQ` | `NSE` | `BSE` | etc.\n"
        "- `sector`: e.g. `Technology`, `Finance`, `Healthcare`\n\n"
        "The authenticated user is recorded as `created_by`."
    ),
    response_description="Newly created company",
)
async def create_company(
    payload: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Company:
    # ── Duplicate ticker guard ──────────────────────────────────────────
    if payload.ticker:
        existing = await db.execute(
            select(Company).where(Company.ticker == payload.ticker)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Company with ticker {payload.ticker} already exists",
            )

    company = Company(
        name=payload.name,
        ticker=payload.ticker,
        sector=payload.sector,
        exchange=payload.exchange,
        description=payload.description,
        created_by=current_user.id,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    logger.info("Created company %s (id=%s)", company.name, company.id)
    return company


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Get a company by ID",
    description="Retrieve a single company by its UUID. Returns **404** if not found.",
    response_description="Company details",
)
async def get_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Company:
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Update a company",
    description=(
        "Partially update any fields on a company. Only fields you include in the request body are changed "
        "(standard JSON Merge Patch behaviour — omitted fields stay untouched).\n\n"
        "Returns **404** if the company does not exist."
    ),
    response_description="Updated company",
)
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Company:
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)
    logger.info("Updated company %s", company_id)
    return company


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company",
    description=(
        "Permanently delete a company and all its associated documents, chunks, and agent runs "
        "(cascade delete). Returns **204 No Content** on success, **404** if not found."
    ),
)
async def delete_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    await db.delete(company)
    await db.commit()
    logger.info("Deleted company %s", company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
