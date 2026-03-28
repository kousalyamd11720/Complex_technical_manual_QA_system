from __future__ import annotations

import re

# Numbered section id + optional title (title may be empty).
# (?![\d.]) prevents "2210.1" from matching as section "22" + junk.
SECTION_HEADING_RE = re.compile(
    r"^\s*(?:Section\s+)?(\d{1,2}(?:\.\d{1,2}){0,6})(?![\d.])(?:\s*[:\-.])?\s*(.*)$",
    re.IGNORECASE,
)

# Line-anchored table caption (exclude "Table of ..." TOC lines).
TABLE_LINE_RE = re.compile(
    r"^\s*(?:Table|TABLE)\s+(?!of\b)([A-Za-z0-9\-\.]+)",
    re.IGNORECASE,
)

# Search anywhere in a cell or line (for markdown tables).
TABLE_CAPTION_SEARCH_RE = re.compile(
    r"(?:Table|TABLE)\s+(?!of\b)([A-Za-z0-9\-\.]+)",
    re.IGNORECASE,
)

# Appendix-style table ids (D-1, G-3).
TABLE_APPENDIX_LABEL_RE = re.compile(
    r"(?:Table|TABLE)\s+(?!of\b)([A-Z]-\d+)",
    re.IGNORECASE,
)

_MAX_CAPTION_LINE_LEN = 220
_DOT_LEADER_SKIP = re.compile(r"\.{18,}")


def normalize_line_for_section_heading(line: str) -> str:
    """Strip list / markdown wrappers so subsection lines match SECTION_HEADING_RE."""
    s = line.strip()
    s = s.lstrip("#").strip()
    s = re.sub(r"^\s*[-*•]\s+", "", s)
    s = re.sub(r"^\s*\*{1,2}(\d{1,2}(?:\.\d{1,2}){0,6})\*{1,2}\s*", r"\1 ", s)
    return s.strip()


def validate_section_id(section_id: str | None) -> str | None:
    """
    Reject OCR/merge noise like '2210.1' (segment >2 digits) while keeping
    handbook-style ids: '2.1', '4.0', '6.7.2'. Optional appendix 'A.1'.
    """
    if not section_id:
        return None
    s = section_id.strip()
    if not s:
        return None
    if re.match(r"^[A-Za-z]\.\d{1,3}(?:\.\d{1,3})*$", s):
        return s
    parts = s.split(".")
    if not parts or len(parts) > 8:
        return None
    for p in parts:
        if not p.isdigit():
            return None
        if len(p) > 2:
            return None
        if int(p) > 99:
            return None
    return s


def parse_section_heading_line(line: str) -> tuple[str, str | None] | None:
    normalized = normalize_line_for_section_heading(line)
    m = SECTION_HEADING_RE.match(normalized)
    if not m:
        return None
    section_id = validate_section_id(m.group(1))
    if not section_id:
        return None
    title = (m.group(2) or "").strip() or None
    return (section_id, title)


def infer_section_from_table_name(table_name: str | None) -> str | None:
    """
    NASA-style labels: 6.7-1 -> section 6.7; 2.1-1 -> 2.1.
    Appendix-style (D-1, G-3) returns None.
    """
    if not table_name:
        return None
    name = table_name.strip()
    m = re.match(r"^(\d+(?:\.\d+)+)\s*[-–]\s*[\w.]+$", name)
    if m:
        return validate_section_id(m.group(1))
    m = re.match(r"^(\d+(?:\.\d+)+)$", name)
    if m:
        return validate_section_id(m.group(1))
    return None


def normalize_table_label(label: str) -> str:
    """Normalize unicode dashes so 6.7-1 is consistent."""
    return label.replace("–", "-").replace("—", "-").strip()


def _clean_line_for_table_match(line: str) -> str:
    """Strip markdown table pipes so '| Table 6.7-1 | foo' matches."""
    s = line.strip()
    s = s.replace("|", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_toc_noise_line(line: str) -> bool:
    s = line.strip()
    if len(s) > _MAX_CAPTION_LINE_LEN:
        return True
    if _DOT_LEADER_SKIP.search(s):
        return True
    if re.search(r"Table of (Contents|Tables|Figures)\b", s, re.IGNORECASE):
        return True
    return False


def _is_toc_table_index_row(line: str) -> bool:
    """Rows like '| Table 2.1-1 | Table 2.1-1 | ...' (list-of-tables pages)."""
    if line.count("|") < 2:
        return False
    return len(re.findall(r"(?:Table|TABLE)\s+", line)) >= 2


def find_table_caption_in_text(text: str, max_lines: int = 40) -> str | None:
    for line in text.splitlines()[:max_lines]:
        stripped = line.strip()
        if _is_toc_noise_line(stripped):
            continue
        for candidate in (stripped, _clean_line_for_table_match(stripped)):
            m = TABLE_LINE_RE.match(candidate)
            if m:
                return normalize_table_label(m.group(1))
            m = TABLE_CAPTION_SEARCH_RE.search(candidate)
            if m:
                return normalize_table_label(m.group(1))
            m = TABLE_APPENDIX_LABEL_RE.search(candidate)
            if m:
                return normalize_table_label(m.group(1))
    return None


def find_first_table_caption_in_paragraph(text: str) -> str | None:
    """Scan each line (short lines only) for a Table/TABLE caption — not only the first line."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _is_toc_noise_line(stripped):
            continue
        if len(stripped) > _MAX_CAPTION_LINE_LEN:
            continue
        for candidate in (stripped, _clean_line_for_table_match(stripped)):
            m = TABLE_LINE_RE.match(candidate)
            if m:
                return normalize_table_label(m.group(1))
            m = TABLE_CAPTION_SEARCH_RE.search(candidate)
            if m:
                return normalize_table_label(m.group(1))
            m = TABLE_APPENDIX_LABEL_RE.search(candidate)
            if m:
                return normalize_table_label(m.group(1))
    return None


def table_caption_labels_from_page_text(page_text: str) -> list[str]:
    """
    Collect Table/TABLE labels in visual line order for a PDF page (captions often sit above the grid).
    Skips long TOC/dot-leader lines and multi-Table index rows.
    """
    ordered: list[str] = []
    for line in page_text.splitlines():
        stripped = line.strip()
        if _is_toc_noise_line(stripped) or _is_toc_table_index_row(stripped):
            continue
        for candidate in (stripped, _clean_line_for_table_match(stripped)):
            m = TABLE_LINE_RE.match(candidate)
            if not m:
                m = TABLE_CAPTION_SEARCH_RE.search(candidate)
            if not m:
                m = TABLE_APPENDIX_LABEL_RE.search(candidate)
            if m:
                ordered.append(normalize_table_label(m.group(1)))
                break
    return ordered


def merge_page_section_with_inferred(page_sec: str | None, inferred: str | None) -> str | None:
    """
    Combine pdf page section with section inferred from a table label (e.g. 6.7-1 -> 6.7).
    Prefer the more specific id when one is a dotted extension of the other.
    """
    if not inferred:
        return page_sec
    if not page_sec:
        return inferred
    if page_sec.startswith(inferred + "."):
        return page_sec
    if inferred.startswith(page_sec + "."):
        return inferred
    if page_sec.endswith(".0") and page_sec.split(".")[0] == inferred.split(".")[0]:
        return inferred
    ps_parts = page_sec.split(".")
    inf_parts = inferred.split(".")
    if len(ps_parts) == 1 and len(inf_parts) > 1 and inf_parts[0] == ps_parts[0]:
        return inferred
    return page_sec
