from app.services.chunking_service import ChunkingService
from app.services.structure_builder import StructureBuilder


def test_structure_and_chunking():
    records = [
        {"chunk_id": "1", "text": "6.1 System Design", "section": "6.1", "content_type": "text"},
        {"chunk_id": "2", "text": "Section 6.1 introduces SRR and PDR gates." * 30, "section": "6.1.1", "content_type": "text"},
    ]
    enriched = StructureBuilder().enrich(records)
    assert enriched[1]["section_parent"] == "6.1"
    chunks = ChunkingService().chunk_records(enriched, max_chars=200)
    assert len(chunks) >= 2
    assert all("xref_targets" in c for c in chunks)
