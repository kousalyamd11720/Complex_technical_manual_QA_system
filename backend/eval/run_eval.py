from __future__ import annotations

import json
from pathlib import Path

from app.schemas.query import QueryRequest
from app.services.qa_service import QAService


def evaluate() -> None:
    base = Path(__file__).parent
    questions = json.loads((base / "gold_questions.json").read_text(encoding="utf-8"))
    qa = QAService()
    results = []
    for q in questions:
        response = qa.answer(QueryRequest(question=q["question"], top_k=8))
        citation_sections = [c.section for c in response.citations if c.section]
        hits = len(set(q["expected_sections"]).intersection(set(citation_sections)))
        results.append(
            {
                "id": q["id"],
                "question": q["question"],
                "confidence": response.confidence,
                "citation_hits": hits,
                "citations_returned": len(response.citations),
            }
        )
    out_path = base / "results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote evaluation report to {out_path}")


if __name__ == "__main__":
    evaluate()
