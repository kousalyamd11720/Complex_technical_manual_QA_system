from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.parsers.section_heading import (
    find_first_table_caption_in_paragraph,
    find_table_caption_in_text,
    infer_section_from_table_name,
    merge_page_section_with_inferred,
    normalize_line_for_section_heading,
    normalize_table_label,
    parse_section_heading_line,
    table_caption_labels_from_page_text,
    TABLE_LINE_RE,
    validate_section_id,
)

PRINTED_PAGE_RE = re.compile(r"\b(\d{1,3})\b")
PAGE_REF_RE = re.compile(r"\b[Pp]age\s+(\d{1,3})\b")
FIGURE_NAME_RE = re.compile(r"^\s*(?:Figure|FIGURE)\s+([A-Za-z0-9\-\.]+)")


@dataclass
class ParsedRecord:
    chunk_id: str
    text: str
    chapter: str | None
    section: str | None
    section_title: str | None = None
    section_display: str | None = None
    paragraph_id: str | None = None
    content_type: str = "text"
    figure_name: str | None = None
    table_name: str | None = None
    pdf_page_index: int = 0
    printed_page_label: str | None = None
    source: str = ""


class PyMuPDF4LLMParser:
    """
    Parses PDFs with pymupdf4llm and enriches content with section-aware
    paragraph boundaries, table extraction, and diagram OCR metadata.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse(self, pdf_path: str) -> list[ParsedRecord]:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        self.logger.info("PyMuPDF4LLM parse started: %s", pdf_path)

        page_labels = self._read_page_labels(path)
        pages = self._parse_with_pymupdf4llm(path)
        self.logger.info("PyMuPDF4LLM parse extracted pages: %d", len(pages))

        text_records, page_sections, page_printed_labels = self._records_from_pages(
            pages, source="pymupdf4llm", page_labels=page_labels
        )
        self.logger.info("PyMuPDF4LLM normalized text records: %d", len(text_records))

        table_records = self._extract_tables(path, page_sections, page_printed_labels)
        self.logger.info("Extracted table records: %d", len(table_records))

        diagram_records = self._extract_diagrams(path, page_sections, page_printed_labels)
        self.logger.info("Extracted diagram records: %d", len(diagram_records))

        return text_records + table_records + diagram_records

    def _parse_with_pymupdf4llm(self, path: Path) -> list[str]:
        import pymupdf4llm

        self.logger.info("Calling pymupdf4llm.to_markdown(page_chunks=True). OCR output may appear in console.")
        md = pymupdf4llm.to_markdown(str(path), page_chunks=True)
        if isinstance(md, (list, tuple)):
            return [str(p) for p in md]
        if isinstance(md, str):
            return [md]
        raise TypeError(f"Unexpected pymupdf4llm return type: {type(md)}")

    def _flush_paragraph(
        self,
        records: list[ParsedRecord],
        paragraph_lines: list[str],
        section: str | None,
        title: str | None,
        chapter: str | None,
        printed_label: str | None,
        paragraph_index: dict[str, int],
        page_idx: int,
        source: str,
        record_counter: list[int],
    ) -> None:
        if not paragraph_lines:
            return
        text = "\n".join(paragraph_lines).strip()
        if not text:
            return
        content_type = "text"
        figure_name = None
        table_name = None
        work_section = validate_section_id(section)
        work_chapter = chapter

        figure_match = FIGURE_NAME_RE.match(text)
        if figure_match:
            content_type = "figure"
            figure_name = figure_match.group(1)

        lines_nonempty = [ln.strip() for ln in paragraph_lines if ln.strip()]
        first_line = lines_nonempty[0] if lines_nonempty else ""
        table_line_match = TABLE_LINE_RE.match(first_line) if first_line else None
        if not table_line_match and first_line:
            table_line_match = TABLE_LINE_RE.match(normalize_line_for_section_heading(first_line))
        if table_line_match:
            content_type = "table"
            table_name = normalize_table_label(table_line_match.group(1))
        if not table_name:
            table_name = find_first_table_caption_in_paragraph(text)

        if content_type == "table" and table_name:
            inferred = infer_section_from_table_name(table_name)
            if inferred:
                work_section = merge_page_section_with_inferred(work_section, inferred)
                if work_section:
                    work_chapter = work_section.split(".")[0]

        section_key = work_section or "unknown"
        paragraph_index[section_key] = paragraph_index.get(section_key, 0) + 1
        record_counter[0] += 1
        disp = f"{work_section} {title}".strip() if work_section and title else (work_section or title)
        records.append(
            ParsedRecord(
                chunk_id=f"rec-{record_counter[0]}",
                text=text,
                chapter=work_chapter,
                section=work_section,
                section_title=title,
                section_display=disp,
                paragraph_id=f"{section_key}-p{paragraph_index[section_key]}",
                content_type=content_type,
                figure_name=figure_name,
                table_name=table_name,
                pdf_page_index=page_idx,
                printed_page_label=printed_label,
                source=source,
            )
        )

    def _records_from_pages(
        self,
        pages: list[str],
        source: str,
        page_labels: dict[int, str | None],
    ) -> tuple[list[ParsedRecord], dict[int, str | None], dict[int, str | None]]:
        records: list[ParsedRecord] = []
        page_sections: dict[int, str | None] = {}
        page_printed_labels: dict[int, str | None] = {}

        current_section: str | None = None
        current_chapter: str | None = None
        current_title: str | None = None
        paragraph_index: dict[str, int] = {}
        record_counter: list[int] = [0]

        for page_idx, page_md in enumerate(pages):
            printed_label = page_labels.get(page_idx)
            if not printed_label:
                tail_lines = page_md.splitlines()[-12:] if page_md else []
                printed_label = self._extract_printed_page_label(tail_lines)
            page_printed_labels[page_idx] = printed_label
            page_sections[page_idx] = current_section

            blocks = re.split(r"\n\s*\n+", page_md or "")
            for block in blocks:
                block = block.strip()
                if not block:
                    continue
                lines = block.splitlines()
                first_raw = lines[0] if lines else ""
                first_norm = normalize_line_for_section_heading(first_raw)
                parsed = parse_section_heading_line(first_raw) or parse_section_heading_line(first_norm)

                if parsed and len(lines) == 1:
                    current_section, current_title = parsed
                    current_chapter = current_section.split(".")[0] if current_section else None
                    page_sections[page_idx] = current_section
                    continue

                if parsed and len(lines) > 1:
                    current_section, current_title = parsed
                    current_chapter = current_section.split(".")[0] if current_section else None
                    page_sections[page_idx] = current_section
                    self._flush_paragraph(
                        records,
                        lines[1:],
                        current_section,
                        current_title,
                        current_chapter,
                        printed_label,
                        paragraph_index,
                        page_idx,
                        source,
                        record_counter,
                    )
                    continue

                self._flush_paragraph(
                    records,
                    lines,
                    current_section,
                    current_title,
                    current_chapter,
                    printed_label,
                    paragraph_index,
                    page_idx,
                    source,
                    record_counter,
                )

        return records, page_sections, page_printed_labels

    def _extract_tables(
        self,
        path: Path,
        page_sections: dict[int, str | None],
        page_printed_labels: dict[int, str | None],
    ) -> list[ParsedRecord]:
        try:
            import pdfplumber
        except ImportError:
            self.logger.warning("pdfplumber is not installed; skipping table extraction.")
            return []

        out: list[ParsedRecord] = []
        t_idx = 0
        with pdfplumber.open(path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                section = page_sections.get(page_idx)
                printed = page_printed_labels.get(page_idx)
                try:
                    tables = page.extract_tables() or []
                except Exception as exc:
                    self.logger.debug("extract_tables failed page %s: %s", page_idx, exc)
                    continue
                for table in tables:
                    formatted = self._format_table(table)
                    if not formatted or len(formatted.strip()) < 12:
                        continue
                    cap = self._extract_table_name(formatted)
                    work_section = section
                    if cap:
                        inferred = infer_section_from_table_name(cap)
                        work_section = merge_page_section_with_inferred(work_section, inferred)
                    work_section = validate_section_id(work_section)
                    t_idx += 1
                    out.append(
                        ParsedRecord(
                            chunk_id=f"table-{page_idx}-{t_idx}",
                            text=formatted,
                            chapter=work_section.split(".")[0] if work_section else None,
                            section=work_section,
                            section_title=None,
                            section_display=work_section,
                            paragraph_id=None,
                            content_type="table",
                            figure_name=None,
                            table_name=cap,
                            pdf_page_index=page_idx,
                            printed_page_label=printed,
                            source="pdfplumber",
                        )
                    )
        return out

    def _extract_diagrams(
        self,
        path: Path,
        page_sections: dict[int, str | None],
        page_printed_labels: dict[int, str | None],
    ) -> list[ParsedRecord]:
        try:
            import pdfplumber
            import pytesseract
        except ImportError:
            self.logger.warning("pdfplumber or pytesseract missing; skipping diagram OCR.")
            return []

        diagram_records: list[ParsedRecord] = []
        with pdfplumber.open(path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                section = validate_section_id(page_sections.get(page_idx))
                printed_label = page_printed_labels.get(page_idx)
                page_width = float(page.width)
                page_height = float(page.height)
                for img_idx, image_obj in enumerate(page.images or []):
                    x0 = float(image_obj.get("x0", 0))
                    top = float(image_obj.get("top", 0))
                    x1 = float(image_obj.get("x1", 0))
                    bottom = float(image_obj.get("bottom", 0))
                    x0 = max(0.0, min(x0, page_width))
                    x1 = max(0.0, min(x1, page_width))
                    top = max(0.0, min(top, page_height))
                    bottom = max(0.0, min(bottom, page_height))
                    if x1 <= x0 or bottom <= top:
                        self.logger.warning(
                            "Skipping invalid image bbox on page %d image %d: %s",
                            page_idx,
                            img_idx,
                            (x0, top, x1, bottom),
                        )
                        continue
                    bbox = (x0, top, x1, bottom)
                    try:
                        cropped = page.crop(bbox)
                        pil = cropped.to_image(resolution=200).original
                        ocr_text = pytesseract.image_to_string(pil, lang="eng").strip()
                        if not ocr_text:
                            continue
                        figure_name = self._extract_figure_name(ocr_text)
                        printed = printed_label or str(page_idx + 1)
                        diagram_records.append(
                            ParsedRecord(
                                chunk_id=f"diagram-{page_idx}-{img_idx}",
                                text=f"FIGURE OCR (PDF page index {page_idx}, printed page {printed}): {ocr_text}",
                                chapter=section.split(".")[0] if section else None,
                                section=section,
                                section_title=None,
                                section_display=section,
                                paragraph_id=None,
                                content_type="figure",
                                figure_name=figure_name,
                                table_name=None,
                                pdf_page_index=page_idx,
                                printed_page_label=printed_label,
                                source="pdfplumber-ocr",
                            )
                        )
                        self.logger.info(
                            "Diagram OCR extracted figure %s from page %d: %s",
                            figure_name or "unknown",
                            page_idx + 1,
                            ocr_text[:120],
                        )
                    except Exception as exc:
                        self.logger.warning(
                            "Diagram OCR failed for page %d image %d after bbox clamp: %s",
                            page_idx,
                            img_idx,
                            str(exc),
                        )
        return diagram_records

    def _format_table(self, table: list[list[str] | None]) -> str:
        rows = [
            [cell.strip() if isinstance(cell, str) else "" for cell in row]
            for row in table
            if row
        ]
        if not rows:
            return ""
        header = rows[0]
        body = rows[1:]
        divider = ["---" for _ in header]
        lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(divider) + " |"]
        for row in body:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    def _extract_printed_page_label(self, tail_lines: list[str]) -> str | None:
        candidate: str | None = None
        for line in reversed(tail_lines):
            if "nasa" in line.lower():
                continue
            if "page" in line.lower():
                match = PAGE_REF_RE.search(line)
                if match:
                    return match.group(1)
            matches = PRINTED_PAGE_RE.findall(line)
            if not matches:
                continue
            if re.fullmatch(r"\d{1,3}", line.strip()):
                return matches[-1]
            if re.search(r"^\D*\d{1,3}\D*$", line) and len(line.strip()) <= 5:
                candidate = matches[-1]
        return candidate

    def _extract_figure_name(self, text: str) -> str | None:
        match = FIGURE_NAME_RE.match(text)
        if match:
            return match.group(1)
        m = re.search(r"(?:Figure|FIGURE)\s+([A-Za-z0-9\-\.]+)", text)
        if m:
            return m.group(1)
        return None

    def _extract_table_name(self, text: str) -> str | None:
        return find_table_caption_in_text(text, max_lines=15)

    def _read_page_labels(self, path: Path) -> dict[int, str | None]:
        labels: dict[int, str | None] = {}
        try:
            import fitz
        except ImportError:
            self.logger.debug("pymupdf is not installed; skipping page label extraction.")
            return labels

        try:
            doc = fitz.open(str(path))
            for page_idx, page in enumerate(doc):
                label = page.get_label()
                if label and label.strip():
                    labels[page_idx] = label.strip()
            doc.close()
        except Exception as exc:
            self.logger.warning("Failed to read PDF page labels: %s", str(exc))
        return labels
