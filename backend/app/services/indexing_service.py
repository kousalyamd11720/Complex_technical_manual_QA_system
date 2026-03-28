from __future__ import annotations

import logging

from app.core.config import get_settings
from app.embeddings.hf_embedder import HFEmbedder
from app.storage.bm25_store import BM25Store
from app.storage.chroma_store import ChromaStore


class IndexingService:
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.embedder = HFEmbedder(
            self.settings.embedding_model_name,
            batch_size=self.settings.embedding_batch_size,
        )
        self.chroma = ChromaStore(self.settings.chroma_dir)
        self.bm25 = BM25Store(self.settings.bm25_path)

    def build(self, chunks: list[dict]) -> None:
        self.logger.info("Embedding documents for vector index: chunks=%d", len(chunks))
        texts = [c["text"] for c in chunks]
        vectors = self.embedder.embed_documents(texts)
        # Filter out chunks with empty vectors
        valid_chunks_vectors = [(c, v) for c, v in zip(chunks, vectors) if v]
        if len(valid_chunks_vectors) != len(chunks):
            self.logger.warning("Filtered out %d chunks with empty embeddings", len(chunks) - len(valid_chunks_vectors))
        valid_chunks, valid_vectors = zip(*valid_chunks_vectors) if valid_chunks_vectors else ([], [])
        self.logger.info("Dense embeddings computed for %d chunks", len(valid_chunks))
        self.chroma.rebuild(list(valid_chunks), list(valid_vectors))
        self.logger.info("Chroma index rebuilt")
        self.bm25.build(list(valid_chunks))
        self.logger.info("BM25 index rebuilt")
