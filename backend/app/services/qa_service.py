from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.llms.gemini_client import GeminiClient
from app.schemas.query import CitationItem, QueryRequest, QueryResponse
from app.services.crossref_service import CrossrefService
from app.services.retrieval_service import RetrievalService
from app.utils.acronyms import expand_acronyms, normalize_acronyms


class QAService:
    def __init__(self):
        self.settings = get_settings()
        self.cache_path = Path(self.settings.data_dir) / "processed" / "query_cache.json"
        self.system_prompt = self._load_system_prompt()

    def answer(self, request: QueryRequest) -> QueryResponse:
        chunks = self._load_chunks()
        retrieval = RetrievalService(chunks)
        crossref = CrossrefService()

        normalized_query = normalize_acronyms(request.question)
        top_k = max(4, min(request.top_k, 8))
        seed = retrieval.hybrid_search(normalized_query, top_k=top_k)
        if not seed:
            seed = chunks[:top_k]
        expanded = crossref.expand(seed, chunks)

        evidence_chunks = [c for c in expanded if c.get("text") and c.get("text").strip()]
        if not evidence_chunks:
            evidence_chunks = seed[:10]
        evidence_chunks = evidence_chunks[:10]

        if not self.settings.gemini_api_key:
            evidence_texts = [c.get("text", "") for c in evidence_chunks if c.get("text")]
            answer_text = (
                "Gemini API key is not configured (GEMINI_API_KEY missing). "
                "Here are the most relevant evidence excerpts I found:\n\n"
                + "\n\n---\n\n".join(evidence_texts)
            )
            prompt = ""
        elif not evidence_chunks or all(not (c.get("text") or "").strip() for c in evidence_chunks):
            answer_text = (
                "The evidence provided is insufficient to answer the question. "
                "I could not find a definition or relevant explanation in the retrieved NASA documents."
            )
            prompt = ""
        else:
            llm = GeminiClient(api_key=self.settings.gemini_api_key, model_name=self.settings.gemini_model)
            prompt = self._build_prompt(request.question, evidence_chunks)
            answer_text = llm.generate(prompt).strip()
            if not answer_text:
                answer_text = "The evidence provided is insufficient to answer the question."
            answer_text = expand_acronyms(answer_text)

        citations = [self._citation_from_chunk(c, reason="hybrid+crossref") for c in evidence_chunks[:10]]
        query_id = str(uuid.uuid4())
        payload = {
            "query_id": query_id,
            "answer": answer_text,
            "confidence": round(min(0.95, 0.55 + (0.05 * len(citations))), 2),
            "citations": [c.model_dump() for c in citations],
            "debug": {"seed_count": len(seed), "expanded_count": len(expanded)},
        }
        self._save_query_payload(payload)
        return QueryResponse(**payload)

    def get_citations(self, query_id: str) -> dict | None:
        if not self.cache_path.exists():
            return None
        payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        return payload.get(query_id)

    def _load_system_prompt(self) -> str:
        prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "answer_prompt.txt"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()
        return (
            "You are a technical handbook QA assistant. Use only the provided evidence chunks. "
            "If evidence is insufficient, explicitly state that the answer cannot be determined from the retrieved evidence. "
            "Always include section/page/paragraph citations when the answer is based on evidence."
        )

    def _build_prompt(self, question: str, evidence_chunks: list[dict]) -> str:
        evidence = []
        for i, c in enumerate(evidence_chunks, start=1):
            section = c.get("section") or "Unknown"
            title = c.get("section_title") or "not available"
            printed = c.get("printed_page_label")
            pdf_idx = c.get("pdf_page_index")
            page_line = (
                f"Printed page: {printed}"
                if printed is not None
                else (f"PDF page index (0-based): {pdf_idx}" if pdf_idx is not None else "Page: unknown")
            )
            if printed is not None and pdf_idx is not None:
                page_line += f" | PDF index (0-based): {pdf_idx}"
            figure_name = c.get("figure_name")
            table_name = c.get("table_name")
            content_type = c.get("content_type") or c.get("type") or "text"
            ref_line = ""
            if figure_name:
                ref_line = f"Figure id: {figure_name}"
            elif table_name:
                ref_line = f"Table id: {table_name}"
            evidence.append(
                "[Chunk %d]\n"
                "Section id: %s\n"
                "Section title: %s\n"
                "%s\n"
                "Content type: %s\n"
                "%s\n"
                "Content:\n%s"
                % (
                    i,
                    section,
                    title,
                    page_line,
                    content_type,
                    ref_line,
                    c.get("text"),
                )
            )
        system = self.system_prompt.strip()
        return (
            f"{system}\n\n"
            "Use only the provided evidence. Cite using printed page numbers when present. "
            "Do not invent section or page labels. "
            "For process or lifecycle questions, cover downward and upward flow and iteration when the evidence supports it. "
            "For figure/table chunks, explain what the visual represents in one short sentence tied to the text.\n\n"
            f"Question: {question}\n\n"
            f"Evidence chunks:\n" + "\n\n".join(evidence)
        )

    def _is_caption_only(self, text: str) -> bool:
        if not text:
            return False
        normalized = text.strip()
        if len(normalized.split()) > 60:
            return False
        upper = normalized.upper()
        if upper.startswith("FIGURE") or upper.startswith("TABLE"):
            return True
        if "FIGURE" in upper and "MINIATURE" in upper:
            return True
        return False

    def _citation_from_chunk(self, chunk: dict, reason: str) -> CitationItem:
        paragraph_id = chunk.get("paragraph_id") or (
            ", ".join(chunk.get("paragraph_ids", [])) if chunk.get("paragraph_ids") else None
        )
        section = chunk.get("section")
        printed_raw = chunk.get("printed_page_label")
        if printed_raw is not None:
            printed_page = str(printed_raw).strip()
        elif chunk.get("pdf_page_index") is not None:
            printed_page = str(int(chunk["pdf_page_index"]) + 1)
        else:
            printed_page = None
        figure_name = chunk.get("figure_name")
        table_name = chunk.get("table_name")
        section_display = chunk.get("section_display") or section
        inner: list[str] = []
        if printed_page is not None:
            inner.append(f"Page {printed_page}")
        if table_name:
            inner.append(f"Table {table_name}")
        elif figure_name:
            inner.append(f"Figure {figure_name}")
        display = None
        if section:
            if inner:
                display = f"Section {section} ({', '.join(inner)})"
            else:
                display = f"Section {section}"
        elif inner:
            display = f"({', '.join(inner)})"
        return CitationItem(
            chunk_id=chunk["chunk_id"],
            chapter=chunk.get("chapter"),
            section=section,
            section_display=section_display,
            paragraph_id=paragraph_id,
            printed_page_label=printed_raw,
            pdf_page_index=chunk.get("pdf_page_index"),
            content_type=chunk.get("content_type"),
            figure_name=figure_name,
            display=display,
            confidence=float(chunk.get("retrieval_score", 0.6)),
            reason=reason,
            text=chunk.get("text", "")[:450],
        )

    def _save_query_payload(self, payload: dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self.cache_path.exists():
            db = json.loads(self.cache_path.read_text(encoding="utf-8"))
        else:
            db = {}
        db[payload["query_id"]] = payload
        self.cache_path.write_text(json.dumps(db, indent=2), encoding="utf-8")

    def _load_chunks(self) -> list[dict]:
        path = Path(self.settings.chunks_jsonl_path)
        if not path.exists():
            raise FileNotFoundError("Chunks file not found. Run /api/ingest first.")
        rows: list[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows
