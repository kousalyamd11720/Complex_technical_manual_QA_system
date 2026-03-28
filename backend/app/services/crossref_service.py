from __future__ import annotations

from collections import defaultdict


class CrossrefService:
    def expand(self, seed_chunks: list[dict], all_chunks: list[dict], limit: int = 14) -> list[dict]:
        by_section: dict[str, list[dict]] = defaultdict(list)
        children_by_parent: dict[str, list[str]] = defaultdict(list)
        by_fig: list[dict] = []
        by_table: list[dict] = []
        by_id = {c["chunk_id"]: c for c in all_chunks}

        for c in all_chunks:
            section = c.get("section")
            if section:
                by_section[section].append(c)
            if c.get("content_type") in {"figure", "diagram"}:
                by_fig.append(c)
            if c.get("content_type") == "table":
                by_table.append(c)

        for section in by_section:
            parent = self._parent_section(section)
            children_by_parent[parent].append(section)

        collected: dict[str, dict] = {c["chunk_id"]: c for c in seed_chunks}

        for chunk in seed_chunks:
            section = chunk.get("section")
            if section:
                for candidate in by_section.get(section, [])[:3]:
                    collected[candidate["chunk_id"]] = candidate
                parent = self._parent_section(section)
                if parent and by_section.get(parent):
                    collected[by_section[parent][0]["chunk_id"]] = by_section[parent][0]
                for child_section in children_by_parent.get(section, [])[:2]:
                    for candidate in by_section.get(child_section, [])[:1]:
                        collected[candidate["chunk_id"]] = candidate
            for ref in chunk.get("xref_targets", []):
                if ref.startswith("section:"):
                    target = ref.split(":", 1)[1]
                    for candidate in by_section.get(target, [])[:3]:
                        collected[candidate["chunk_id"]] = candidate
                elif ref.startswith("figure:") or ref.startswith("table:"):
                    key = ref.split(":", 1)[1].strip()
                    for c in all_chunks:
                        fn = c.get("figure_name") or c.get("table_name")
                        if not fn:
                            continue
                        if str(fn).strip() == key:
                            collected[c["chunk_id"]] = c
                            break
            if len(collected) >= len(seed_chunks) + limit:
                break

        for rel in (by_fig[:2] + by_table[:2]):
            collected.setdefault(rel["chunk_id"], rel)

        return list(collected.values())

    def _parent_section(self, section: str | None) -> str | None:
        if not section or "." not in section:
            return None
        return ".".join(section.split(".")[:-1])
