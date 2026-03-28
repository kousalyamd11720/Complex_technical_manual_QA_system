from __future__ import annotations

from collections import defaultdict

from app.utils.references import extract_references


class ChunkingService:
    def chunk_records(self, records: list[dict], max_chars: int = 1200) -> list[dict]:
        chunks: list[dict] = []
        idx = 0
        sections: dict[str, list[dict]] = defaultdict(list)
        for record in records:
            section = record.get("section") or "root"
            sections[section].append(record)

        for section, section_records in sections.items():
            section_records.sort(key=lambda rec: (rec.get("pdf_page_index", 0), rec.get("paragraph_id") or ""))
            current_texts: list[str] = []
            current_paragraph_ids: list[str] = []
            current_meta: dict = {}
            current_len = 0

            def flush_current() -> None:
                nonlocal idx, current_texts, current_paragraph_ids, current_len, current_meta
                if not current_texts:
                    return
                idx += 1
                combined = "\n\n".join(current_texts).strip()
                chunk = self._make_chunk(current_meta, combined, idx, paragraph_ids=current_paragraph_ids)
                chunk["paragraph_ids"] = current_paragraph_ids.copy()
                chunks.append(chunk)
                current_texts = []
                current_paragraph_ids = []
                current_len = 0
                current_meta = {}

            for rec in section_records:
                text = (rec.get("text") or "").strip()
                if not text:
                    continue
                if rec.get("content_type") != "text":
                    flush_current()
                    idx += 1
                    chunks.append(self._make_chunk(rec, text, idx, paragraph_ids=[]))
                    continue
                rec_paragraph_id = rec.get("paragraph_id")
                if len(text) > max_chars:
                    flush_current()
                    for split_chunk in self._split_long_text(rec, max_chars, idx):
                        idx += 1
                        chunks.append(split_chunk)
                    continue
                if not current_texts or current_len + len(text) + 2 <= max_chars:
                    if not current_texts:
                        current_meta = rec
                    current_texts.append(text)
                    if rec_paragraph_id:
                        current_paragraph_ids.append(rec_paragraph_id)
                    current_len += len(text) + 2
                else:
                    flush_current()
                    current_meta = rec
                    current_texts.append(text)
                    current_paragraph_ids = [rec_paragraph_id] if rec_paragraph_id else []
                    current_len = len(text) + 2
            flush_current()

        return chunks

    def _split_long_text(self, rec: dict, max_chars: int, start_idx: int) -> list[dict]:
        text = (rec.get("text") or "").strip()
        chunks: list[dict] = []
        start = 0
        overlap = 120
        split_index = 0
        while start < len(text):
            split_index += 1
            idx = start_idx + split_index
            part = text[start : start + max_chars]
            chunk = self._make_chunk(rec, part, idx, paragraph_ids=[rec.get("paragraph_id")])
            chunk["is_split"] = True
            chunk["split_start"] = start
            chunks.append(chunk)
            if start + max_chars >= len(text):
                break
            start += max_chars - overlap
        return chunks

    def _make_chunk(self, rec: dict, text: str, idx: int, paragraph_ids: list[str] | None = None) -> dict:
        section = rec.get("section")
        section_title = rec.get("section_title")
        section_display = f"{section} {section_title}".strip() if section else None
        chunk = {
            "chunk_id": f"chunk-{idx}" if idx else f"chunk-temp-{rec.get('chunk_id')}",
            "text": text,
            "chapter": rec.get("chapter"),
            "section": section,
            "section_title": section_title,
            "section_display": section_display,
            "section_parent": rec.get("section_parent"),
            "section_depth": rec.get("section_depth"),
            "content_type": rec.get("content_type", "text"),
            "type": rec.get("content_type", "text"),
            "pdf_page_index": rec.get("pdf_page_index"),
            "printed_page_label": rec.get("printed_page_label"),
            "paragraph_id": rec.get("paragraph_id"),
            "paragraph_ids": paragraph_ids or [],
            "figure_name": rec.get("figure_name"),
            "table_name": rec.get("table_name"),
            "xref_targets": extract_references(text),
        }
        return chunk