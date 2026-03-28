from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=5, ge=1, le=30)


class CitationItem(BaseModel):
    chunk_id: str
    chapter: str | None = None
    section: str | None = None
    section_display: str | None = None
    paragraph_id: str | None = None
    printed_page_label: str | None = None
    pdf_page_index: int | None = None
    content_type: str | None = None
    figure_name: str | None = None
    display: str | None = None
    confidence: float = 0.0
    reason: str = ""
    text: str = ""


class QueryResponse(BaseModel):
    query_id: str
    answer: str
    confidence: float
    citations: list[CitationItem]
    debug: dict[str, Any] = {}
