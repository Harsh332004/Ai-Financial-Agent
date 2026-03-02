from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid dense+sparse retrieval with RRF fusion and cross-encoder reranking."""

    def __init__(
        self,
        indexer,
        embed_model_name: str = "all-MiniLM-L6-v2",
        rerank_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_k_initial: int = 10,
        top_k_final: int = 3,
    ):
        self.indexer = indexer
        self.embed_model_name = embed_model_name
        self.rerank_model_name = rerank_model_name
        self.top_k_initial = top_k_initial
        self.top_k_final = top_k_final
        self._embed_model = None
        self._rerank_model = None

    def _get_embed_model(self):
        if self._embed_model is None:
            from sentence_transformers import SentenceTransformer
            self._embed_model = SentenceTransformer(self.embed_model_name)
        return self._embed_model

    def _get_rerank_model(self):
        if self._rerank_model is None:
            from sentence_transformers.cross_encoder import CrossEncoder
            self._rerank_model = CrossEncoder(self.rerank_model_name)
        return self._rerank_model

    def retrieve(self, query: str) -> list[dict]:
        """Return top-k chunks ranked by hybrid RRF + cross-encoder score.

        Returns a list of dicts: {chunk_index, text, score}
        """
        if not self.indexer.faiss_index or not self.indexer.chunks:
            logger.warning("Index is empty — cannot retrieve")
            return []

        k = min(self.top_k_initial, len(self.indexer.chunks))

        # ---- Dense retrieval (FAISS) ----
        query_model = self._get_embed_model()
        q_vec = query_model.encode([query], normalize_embeddings=True)
        q_vec = np.array(q_vec, dtype="float32")
        _, faiss_indices = self.indexer.faiss_index.search(q_vec, k)
        faiss_ranks: dict[int, int] = {int(idx): rank for rank, idx in enumerate(faiss_indices[0]) if idx != -1}

        # ---- Sparse retrieval (BM25) ----
        tokenized_query = query.lower().split()
        bm25_scores = self.indexer.bm25_index.get_scores(tokenized_query)
        bm25_top_indices = np.argsort(bm25_scores)[::-1][:k]
        bm25_ranks: dict[int, int] = {int(idx): rank for rank, idx in enumerate(bm25_top_indices)}

        # ---- RRF fusion ----
        all_indices = set(faiss_ranks.keys()) | set(bm25_ranks.keys())
        RRF_K = 60
        rrf_scores: dict[int, float] = {}
        for idx in all_indices:
            score = 0.0
            if idx in faiss_ranks:
                score += 1.0 / (RRF_K + faiss_ranks[idx])
            if idx in bm25_ranks:
                score += 1.0 / (RRF_K + bm25_ranks[idx])
            rrf_scores[idx] = score

        top_candidates = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)[:k]
        candidate_texts = [self.indexer.chunks[i] for i in top_candidates]

        # ---- Cross-encoder reranking ----
        try:
            reranker = self._get_rerank_model()
            pairs = [[query, text] for text in candidate_texts]
            rerank_scores = reranker.predict(pairs)
            ranked = sorted(zip(top_candidates, candidate_texts, rerank_scores), key=lambda x: x[2], reverse=True)
        except Exception as e:
            logger.warning("Cross-encoder reranking failed (%s), using RRF order", e)
            ranked = [(idx, text, rrf_scores[idx]) for idx, text in zip(top_candidates, candidate_texts)]

        results = [
            {"chunk_index": int(idx), "text": text, "score": float(score)}
            for idx, text, score in ranked[: self.top_k_final]
        ]
        return results
