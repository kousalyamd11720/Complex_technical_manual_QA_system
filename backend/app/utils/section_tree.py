from collections import defaultdict


def build_parent_map(section_ids: list[str]) -> dict[str, str | None]:
    known = set(section_ids)
    parent_map: dict[str, str | None] = {}
    for section_id in section_ids:
        parts = section_id.split(".")
        parent = None
        for i in range(len(parts) - 1, 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in known:
                parent = candidate
                break
        parent_map[section_id] = parent
    return parent_map


def build_children_map(parent_map: dict[str, str | None]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = defaultdict(list)
    for child, parent in parent_map.items():
        if parent is not None:
            children[parent].append(child)
    return dict(children)
