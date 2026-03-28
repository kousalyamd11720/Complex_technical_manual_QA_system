from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from app.core.config import get_settings
from app.parsers.pymupdf4llm_parser import PyMuPDF4LLMParser
from app.parsers.page_label_mapper import build_page_mapping
from app.parsers.table_merger import merge_multipage_tables
from app.services.chunking_service import ChunkingService
from app.services.indexing_service import IndexingService
from app.services.structure_builder import StructureBuilder


class IngestionService:
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parser = PyMuPDF4LLMParser()
        self.chunker = ChunkingService()
        self.indexing = IndexingService()
        self.structure = StructureBuilder()

    def ingest(self, pdf_path: str, rebuild_index: bool = True) -> dict:
        self.logger.info("Ingest started: pdf_path=%s rebuild_index=%s", pdf_path, rebuild_index)

        self.logger.info("Step 1/6: parsing PDF (OCR + markdown extraction if needed)")
        parsed = self.parser.parse(pdf_path)
        self.logger.info("Step 1 complete: parsed_records=%d", len(parsed))

        self.logger.info("Step 2/6: enriching with section hierarchy metadata")
        records = [asdict(r) for r in parsed]
        records = self.structure.enrich(records)

        self.logger.info("Step 3/6: merging multi-page tables")
        records = merge_multipage_tables(records)

        self.logger.info("Step 4/6: building printed-page -> pdf-page mapping")
        page_map = build_page_mapping(records)
        for rec in records:
            rec["page_map_resolved_pdf"] = page_map.get(str(rec.get("printed_page_label")))

        self.logger.info(
            "Step 4 complete: records=%d mapped_printed_pages=%d",
            len(records),
            len(page_map),
        )

        self.logger.info("Step 5/6: chunking by semantic boundaries")
        chunks = self.chunker.chunk_records(records)
        self.logger.info("Step 5 complete: chunks=%d", len(chunks))

        self.logger.info("Step 6/6: writing JSONL artifacts")
        self._write_jsonl(Path(self.settings.processed_jsonl_path), records)
        self._write_jsonl(Path(self.settings.chunks_jsonl_path), chunks)

        if rebuild_index:
            self.logger.info("Index build started: dense+sparse indexes")
            self.indexing.build(chunks)
            self.logger.info("Index build finished")

        self.logger.info("Ingest finished successfully")
        return {"status": "ok", "records_count": len(records), "chunks_count": len(chunks)}

    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            for row in rows:
                fp.write(json.dumps(row, ensure_ascii=True) + "\n")
