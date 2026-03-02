from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models.chunk import Chunk
from backend.models.document import Document
from backend.rag.chunker import chunk_text
from backend.rag.indexer import FAISSIndexer
from backend.rag.ocr import extract_text

logger = logging.getLogger(__name__)


async def process_document(document_id: uuid.UUID) -> None:
    """Background task: OCR → chunk → index → update document status.

    Creates its own DB session since it runs in a background task (outside
    the request lifecycle that owns the original session).
    """
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()
            if doc is None:
                logger.error("Document %s not found in background task", document_id)
                return

            logger.info("Starting OCR for document %s (%s)", document_id, doc.filename)

            # ----- OCR -----
            ocr_text = extract_text(doc.file_path)
            page_count = max(1, ocr_text.count("\n\n") + 1)  # rough estimate

            # ----- Chunking -----
            chunks = chunk_text(ocr_text, chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
            logger.info("Created %d chunks from document %s", len(chunks), document_id)

            # ----- Indexing -----
            company_id_str = str(doc.company_id) if doc.company_id else "global"
            indexer = FAISSIndexer(
                index_dir=settings.INDEX_DIR,
                company_id=company_id_str,
                embed_model=settings.EMBED_MODEL,
            )

            # Load existing index so we can append, not overwrite
            indexer.load()
            indexer.add(chunks)
            indexer.save()

            # ----- Save chunk metadata to DB -----
            for i, chunk_text_str in enumerate(chunks):
                chunk = Chunk(
                    document_id=document_id,
                    company_id=doc.company_id,
                    chunk_index=i,
                    chunk_text=chunk_text_str,
                    faiss_id=indexer.faiss_index.ntotal - len(chunks) + i if indexer.faiss_index else None,
                )
                db.add(chunk)

            # ----- Update document -----
            doc.ocr_text = ocr_text
            doc.page_count = page_count
            doc.status = "ready"

            await db.commit()
            logger.info("Document %s processed successfully", document_id)

        except Exception as exc:
            logger.exception("Failed to process document %s: %s", document_id, exc)
            try:
                result = await db.execute(select(Document).where(Document.id == document_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "failed"
                    await db.commit()
            except Exception:
                pass
