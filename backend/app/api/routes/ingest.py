from fastapi import APIRouter, HTTPException

from app.schemas.ingest import IngestRequest, IngestResponse
from app.services.ingestion_service import IngestionService

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest_document(request: IngestRequest) -> IngestResponse:
    service = IngestionService()
    try:
        result = service.ingest(pdf_path=request.pdf_path, rebuild_index=request.rebuild_index)
        return IngestResponse(**result)
    except Exception as exc:  # pragma: no cover - top-level API guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc
