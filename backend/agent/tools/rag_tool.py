from __future__ import annotations

import logging

from backend.config import settings
from backend.rag.indexer import FAISSIndexer
from backend.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


def rag_search(query: str, company_id: str) -> dict:
    """Search the company's FAISS+BM25 index with hybrid retrieval.

    Returns:
        {"results": [{"chunk_index": int, "text": str, "score": float}]}
    """
    try:
        indexer = FAISSIndexer(
            index_dir=settings.INDEX_DIR,
            company_id=company_id,
            embed_model=settings.EMBED_MODEL,
        )
        loaded = indexer.load()
        if not loaded:
            return {"results": [], "error": f"No index found for company {company_id}"}

        retriever = HybridRetriever(
            indexer=indexer,
            embed_model_name=settings.EMBED_MODEL,
            rerank_model_name=settings.RERANK_MODEL,
            top_k_initial=settings.TOP_K_INITIAL,
            top_k_final=settings.TOP_K_FINAL,
        )
        results = retriever.retrieve(query)
        return {"results": results}
    except Exception as e:
        logger.error("RAG search failed: %s", e)
        return {"results": [], "error": str(e)}
