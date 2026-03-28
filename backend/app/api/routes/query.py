from fastapi import APIRouter, HTTPException

from app.schemas.query import QueryRequest, QueryResponse
from app.services.qa_service import QAService

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def ask_question(request: QueryRequest) -> QueryResponse:
    service = QAService()
    try:
        return service.answer(request)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
