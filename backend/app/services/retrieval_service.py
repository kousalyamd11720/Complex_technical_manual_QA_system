from __future__ import annotations

from collections import defaultdict

from app.core.config import get_settings
from app.embeddings.hf_embedder import HFEmbedder
from app.storage.bm25_store import BM25Store
from app.storage.chroma_store import ChromaStore


class RetrievalService:
    def __init__(self, chunks: list[dict]):
        settings = get_settings()
        self.chunks_by_id = {c["chunk_id"]: c for c in chunks}
        # Embeddings can fail due to environment mismatches (e.g., torch/numpy builds).
        # If that happens, we fall back to sparse BM25-only retrieval so /api/query stays functional.
        self.embedder: HFEmbedder | None
        try:
            self.embedder = HFEmbedder(settings.embedding_model_name)
        except Exception:
            self.embedder = None
        self.chroma = ChromaStore(settings.chroma_dir)
        self.bm25 = BM25Store(settings.bm25_path)
        self.bm25.load(chunks)

    def hybrid_search(self, query: str, top_k: int) -> list[dict]:
        dense: list[tuple[str, float]] = []
        if self.embedder is not None:
            try:
                query_vec = self.embedder.embed_query(query)
                raw = self.chroma.query(query_vec, top_k=top_k * 2)
                dense = [(cid, s) for cid, s in raw if cid in self.chunks_by_id]
            except Exception:
                dense = []
        sparse = self.bm25.search(query, top_k=top_k * 2)
        fused = self._rrf(dense, sparse)

        for cid, score in list(fused.items()):
            chunk_text = self.chunks_by_id.get(cid, {}).get("text", "")
            if self._is_caption_only(chunk_text):
                fused[cid] = score * 0.7

        ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [self.chunks_by_id[cid] | {"retrieval_score": score} for cid, score in ranked if cid in self.chunks_by_id]

    def _is_caption_only(self, text: str) -> bool:
        if not text:
            return False
        normalized = text.strip()
        if len(normalized.split()) > 60:
            return False
        upper = normalized.upper()
        if upper.startswith("FIGURE") or upper.startswith("TABLE"):
            return True
        if "FIGURE" in upper and "MINIATURE" in upper:
            return True
        return False

    def _rrf(self, dense: list[tuple[str, float]], sparse: list[tuple[str, float]], k: int = 60) -> dict[str, float]:
        scores: dict[str, float] = defaultdict(float)
        for rank, (cid, _) in enumerate(dense, start=1):
            scores[cid] += 1.0 / (k + rank)
        for rank, (cid, _) in enumerate(sparse, start=1):
            scores[cid] += 1.0 / (k + rank)
        return dict(scores)
