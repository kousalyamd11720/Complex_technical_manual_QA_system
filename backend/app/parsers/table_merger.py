from __future__ import annotations


def merge_multipage_tables(records: list[dict]) -> list[dict]:
    """
    Simple heuristic merge:
    - same section
    - content_type == table
    - starts with similar header prefix
    """
    merged: list[dict] = []
    active: dict | None = None
    for rec in records:
        if rec.get("content_type") != "table":
            if active:
                merged.append(active)
                active = None
            merged.append(rec)
            continue
        if active is None:
            active = rec.copy()
            active["pdf_page_range"] = [rec.get("pdf_page_index"), rec.get("pdf_page_index")]
            continue
        same_section = active.get("section") == rec.get("section")
        active_head = (active.get("text") or "")[:80]
        rec_head = (rec.get("text") or "")[:80]
        similar_header = active_head.split("|")[0:2] == rec_head.split("|")[0:2]
        if same_section and similar_header:
            active["text"] = f"{active.get('text', '')}\n{rec.get('text', '')}".strip()
            active["pdf_page_range"][1] = rec.get("pdf_page_index")
        else:
            merged.append(active)
            active = rec.copy()
            active["pdf_page_range"] = [rec.get("pdf_page_index"), rec.get("pdf_page_index")]
    if active:
        merged.append(active)
    return merged
