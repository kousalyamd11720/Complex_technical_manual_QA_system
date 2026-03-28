from fastapi import APIRouter, HTTPException

from app.services.qa_service import QAService

router = APIRouter()


@router.get("/citations/{query_id}")
def get_citations(query_id: str) -> dict:
    service = QAService()
    payload = service.get_citations(query_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="query_id not found")
    return payload
