from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class FAISSIndexer:
    """Per-company FAISS + BM25 index manager."""

    def __init__(self, index_dir: str, company_id: str, embed_model: str = "all-MiniLM-L6-v2"):
        self.index_dir = Path(index_dir)
        self.company_id = company_id
        self.embed_model_name = embed_model

        self._faiss_path = self.index_dir / f"company_{company_id}.index"
        self._bm25_path = self.index_dir / f"company_{company_id}_bm25.pkl"
        self._chunks_path = self.index_dir / f"company_{company_id}_chunks.pkl"

        self.faiss_index = None
        self.bm25_index = None
        self.chunks: list[str] = []
        self._model = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.embed_model_name)
        return self._model

    def _embed(self, texts: list[str]) -> np.ndarray:
        model = self._get_model()
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(embeddings, dtype="float32")

    def _build_bm25(self, chunks: list[str]):
        from rank_bm25 import BM25Okapi
        tokenized = [c.lower().split() for c in chunks]
        return BM25Okapi(tokenized)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, chunks: list[str]) -> None:
        """Build a fresh index from scratch."""
        import faiss
        self.chunks = chunks
        if not chunks:
            logger.warning("No chunks provided — index will be empty")
            return

        embeddings = self._embed(chunks)
        dim = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dim)
        self.faiss_index.add(embeddings)
        self.bm25_index = self._build_bm25(chunks)
        logger.info("Built FAISS index with %d vectors (dim=%d) for company %s", len(chunks), dim, self.company_id)

    def add(self, new_chunks: list[str]) -> None:
        """Append new chunks to an existing index (or build if empty)."""
        if not self.faiss_index:
            self.build(new_chunks)
            return

        embeddings = self._embed(new_chunks)
        self.faiss_index.add(embeddings)
        self.chunks.extend(new_chunks)
        self.bm25_index = self._build_bm25(self.chunks)

    def save(self) -> None:
        import faiss
        self.index_dir.mkdir(parents=True, exist_ok=True)
        if self.faiss_index is not None:
            faiss.write_index(self.faiss_index, str(self._faiss_path))
        with open(self._bm25_path, "wb") as f:
            pickle.dump(self.bm25_index, f)
        with open(self._chunks_path, "wb") as f:
            pickle.dump(self.chunks, f)
        logger.info("Saved FAISS+BM25 index for company %s", self.company_id)

    def load(self) -> bool:
        """Load index from disk. Returns True if successful."""
        import faiss
        if not self._faiss_path.exists():
            return False
        try:
            self.faiss_index = faiss.read_index(str(self._faiss_path))
            with open(self._bm25_path, "rb") as f:
                self.bm25_index = pickle.load(f)
            with open(self._chunks_path, "rb") as f:
                self.chunks = pickle.load(f)
            logger.info("Loaded FAISS index (%d vectors) for company %s", self.faiss_index.ntotal, self.company_id)
            return True
        except Exception as e:
            logger.error("Failed to load index for company %s: %s", self.company_id, e)
            return False
