from __future__ import annotations

import json
from pathlib import Path

from rank_bm25 import BM25Okapi


class BM25Store:
    def __init__(self, path: str):
        self.path = Path(path)
        self.bm25: BM25Okapi | None = None
        self.chunk_ids: list[str] = []

    def build(self, chunks: list[dict]) -> None:
        tokenized = [self._tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(tokenized)
        self.chunk_ids = [c["chunk_id"] for c in chunks]
        self.path.write_text(json.dumps({"chunk_ids": self.chunk_ids}, indent=2), encoding="utf-8")

    def load(self, chunks: list[dict]) -> None:
        tokenized = [self._tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(tokenized)
        # Must match tokenized row order; persisted chunk_ids go stale after re-ingest or count changes.
        self.chunk_ids = [c["chunk_id"] for c in chunks]

    def search(self, query: str, top_k: int = 8) -> list[tuple[str, float]]:
        if self.bm25 is None:
            return []
        scores = self.bm25.get_scores(self._tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.chunk_ids[i], float(score)) for i, score in ranked]

    def _tokenize(self, text: str) -> list[str]:
        return [tok for tok in text.lower().split() if tok]
