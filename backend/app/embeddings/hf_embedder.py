from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer


class HFEmbedder:
    def __init__(self, model_name: str, batch_size: int = 32):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Loading embedding model: %s", model_name)
        try:
            self.model = SentenceTransformer(model_name)
            self.logger.info("Embedding model loaded successfully")
        except Exception as e:
            self.logger.error("Failed to load embedding model: %s", str(e))
            raise
        self.batch_size = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Filter out empty texts
        valid_texts = [(i, t) for i, t in enumerate(texts) if t and isinstance(t, str)]
        if len(valid_texts) != len(texts):
            self.logger.warning("Filtered out %d empty or invalid texts", len(texts) - len(valid_texts))
        total = len(valid_texts)
        vectors: list[list[float]] = [[] for _ in texts]  # placeholder for all
        for start in range(0, total, self.batch_size):
            end = min(total, start + self.batch_size)
            self.logger.info(
                "Embedding chunks: %d/%d (batch %d..%d)",
                end,
                total,
                start,
                end - 1,
            )
            batch_indices_texts = valid_texts[start:end]
            batch_texts = [t for _, t in batch_indices_texts]
            try:
                batch_vectors = self.model.encode(
                    batch_texts,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                )
                for (orig_idx, _), vec in zip(batch_indices_texts, batch_vectors):
                    vectors[orig_idx] = vec.tolist()
            except Exception as e:
                self.logger.error("Error embedding batch %d..%d: %s", start, end - 1, str(e))
                raise
        return vectors

    def embed_query(self, text: str) -> list[float]:
        vec = self.model.encode([text], normalize_embeddings=True)[0]
        return vec.tolist()
