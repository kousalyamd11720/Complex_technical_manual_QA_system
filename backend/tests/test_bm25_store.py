from app.storage.bm25_store import BM25Store


def test_load_chunk_ids_match_corpus(tmp_path):
    """Regression: chunk_ids must align with tokenized rows (same order as chunks)."""
    path = tmp_path / "bm25.json"
    store = BM25Store(str(path))
    chunks = [
        {"chunk_id": "chunk-a", "text": "alpha beta"},
        {"chunk_id": "chunk-b", "text": "gamma delta"},
    ]
    store.build(chunks)
    # Simulate re-ingest: new chunk set, file on disk still has old ids from build()
    revised = [
        {"chunk_id": "chunk-new-1", "text": "first document"},
        {"chunk_id": "chunk-new-2", "text": "second document"},
        {"chunk_id": "chunk-new-3", "text": "third document"},
    ]
    store.load(revised)
    assert store.chunk_ids == ["chunk-new-1", "chunk-new-2", "chunk-new-3"]
    hits = store.search("second", top_k=2)
    assert hits and hits[0][0] == "chunk-new-2"
