from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    gemini_api_key: str = Field(default="", description="Set GEMINI_API_KEY in environment or .env")
    gemini_model: str = "models/gemini-2.5-flash"
    # Smaller model for faster indexing on ~4k chunks.
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    data_dir: str = "backend/data"
    chroma_dir: str = "backend/data/indexes/chroma"
    bm25_path: str = "backend/data/indexes/bm25.json"
    processed_jsonl_path: str = "backend/data/processed/records.jsonl"
    chunks_jsonl_path: str = "backend/data/processed/chunks.jsonl"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_data_dirs(self) -> None:
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)
        Path(self.processed_jsonl_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.chunks_jsonl_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.bm25_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_data_dirs()
    return settings
