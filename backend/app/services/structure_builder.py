from __future__ import annotations

from app.utils.section_tree import build_parent_map


class StructureBuilder:
    def enrich(self, records: list[dict]) -> list[dict]:
        section_ids = sorted({r["section"] for r in records if r.get("section")})
        parent_map = build_parent_map(section_ids)
        section_titles: dict[str, str] = {}
        for rec in records:
            section = rec.get("section")
            title = rec.get("section_title")
            if section and title and title.strip():
                section_titles.setdefault(section, title.strip())
        for rec in records:
            section = rec.get("section")
            rec["section_parent"] = parent_map.get(section) if section else None
            rec["section_depth"] = len(section.split(".")) if section else 0
            rec["section_title"] = section_titles.get(section)
        return records
