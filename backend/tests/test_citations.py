from app.schemas.query import CitationItem


def test_citation_schema():
    citation = CitationItem(
        chunk_id="chunk-1",
        section="6.3.2",
        printed_page_label="112",
        pdf_page_index=126,
        confidence=0.78,
        reason="hybrid+crossref",
        text="Verification plan content",
    )
    assert citation.section == "6.3.2"
    assert citation.pdf_page_index == 126
