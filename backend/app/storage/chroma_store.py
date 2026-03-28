from __future__ import annotations

from chromadb import PersistentClient


class ChromaStore:
    def __init__(self, persist_dir: str, collection_name: str = "nasa_manual"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.client = PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def rebuild(self, chunks: list[dict], vectors: list[list[float]]) -> None:
        # Delete and recreate collection to clear all data
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass  # Collection might not exist
        self.collection = self.client.create_collection(name=self.collection_name)
        self.collection.add(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=vectors,
            documents=[c["text"] for c in chunks],
            metadatas=[self._metadata(c) for c in chunks],
        )

    def query(self, vector: list[float], top_k: int) -> list[tuple[str, float]]:
        result = self.collection.query(query_embeddings=[vector], n_results=top_k)
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [(chunk_id, 1.0 / (1.0 + float(dist))) for chunk_id, dist in zip(ids, distances)]

    def _metadata(self, chunk: dict) -> dict:
        return {
            "chapter": chunk.get("chapter") or "",
            "section": chunk.get("section") or "",
            "section_parent": chunk.get("section_parent") or "",
            "section_depth": str(chunk.get("section_depth") or ""),
            "section_title": chunk.get("section_title") or "",
            "paragraph_id": chunk.get("paragraph_id") or "",
            "content_type": chunk.get("content_type") or "text",
            "pdf_page_index": str(chunk.get("pdf_page_index") or ""),
            "printed_page_label": str(chunk.get("printed_page_label") or ""),
            "source": chunk.get("source") or "",
            "figure_name": chunk.get("figure_name") or "",
            "table_name": chunk.get("table_name") or "",
        }
