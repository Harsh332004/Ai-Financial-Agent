from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.document import Document
from backend.models.user import User
from backend.schemas.document import DocumentResponse
from backend.services.auth_service import get_current_user
from backend.services.document_service import process_document

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a financial document",
    description=(
        "Upload a PDF or image file to associate with a company.\n\n"
        "**Processing pipeline (runs in the background):**\n"
        "1. File is saved to disk with a UUID filename\n"
        "2. Document record is created with `status: processing`\n"
        "3. OCR extracts text (pymupdf for digital PDFs, EasyOCR for scanned pages/images)\n"
        "4. Text is split into overlapping 300-word chunks\n"
        "5. Chunks are embedded and indexed into FAISS + BM25 per company\n"
        "6. Document `status` updates to `ready` (or `failed`)\n\n"
        "**Accepted formats:** `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp`\n\n"
        "**doc_type options:** `annual_report` | `earnings` | `balance_sheet` | `news` | `other`"
    ),
    response_description="Document record with status=processing (processing continues in background)",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The document file to upload"),
    company_id: uuid.UUID = Form(..., description="UUID of the company this document belongs to"),
    doc_type: str | None = Form(None, description="Document category: annual_report | earnings | balance_sheet | news | other"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    # Validate that the company exists before saving the file
    from backend.models.company import Company
    result = await db.execute(select(Company).where(Company.id == company_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id '{company_id}' not found. Create the company first via POST /companies.",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}{suffix}"
    file_path = upload_dir / unique_filename

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    logger.info("Uploaded file %s -> %s", file.filename, file_path)

    doc = Document(
        company_id=company_id,
        filename=unique_filename,
        original_filename=file.filename or unique_filename,
        doc_type=doc_type,
        file_path=str(file_path),
        status="processing",
        uploaded_by=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(process_document, doc.id)
    return doc


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List documents",
    description=(
        "Return all uploaded documents, sorted by upload date (newest first).\n\n"
        "Filter by `company_id` to list only documents for one company."
    ),
    response_description="Array of document records",
)
async def list_documents(
    company_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    query = select(Document).order_by(Document.uploaded_at.desc())
    if company_id is not None:
        query = query.where(Document.company_id == company_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description=(
        "Retrieve metadata for a single document, including its current `status`.\n\n"
        "- `processing` — OCR and indexing are still running in the background\n"
        "- `ready` — document is indexed and available for agent queries\n"
        "- `failed` — processing encountered an error (check server logs)"
    ),
    response_description="Document metadata",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description=(
        "Delete a document record from the database **and** remove the file from disk. "
        "All associated text chunks are also deleted (cascade). "
        "Returns **204 No Content** on success."
    ),
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except OSError as e:
        logger.warning("Could not delete file %s: %s", doc.file_path, e)

    await db.delete(doc)
    await db.commit()
    logger.info("Deleted document %s", document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
