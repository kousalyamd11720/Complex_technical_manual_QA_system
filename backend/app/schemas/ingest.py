from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    pdf_path: str = Field(..., description="Absolute or workspace-relative PDF path")
    rebuild_index: bool = True


class IngestResponse(BaseModel):
    status: str
    records_count: int
    chunks_count: int
