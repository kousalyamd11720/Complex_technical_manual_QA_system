import re


SECTION_REF_RE = re.compile(r"\b[Ss]ection\s+(\d+(?:\.\d+)*)\b")
FIGURE_REF_RE = re.compile(r"\b[Ff]igure\s+([A-Za-z0-9\-]+)\b")
TABLE_REF_RE = re.compile(r"\b[Tt]able\s+(?!of\b)([A-Za-z0-9\-]+)\b")


def extract_references(text: str) -> list[str]:
    refs: list[str] = []
    refs.extend(f"section:{m.group(1)}" for m in SECTION_REF_RE.finditer(text))
    refs.extend(f"figure:{m.group(1)}" for m in FIGURE_REF_RE.finditer(text))
    refs.extend(f"table:{m.group(1)}" for m in TABLE_REF_RE.finditer(text))
    return refs
