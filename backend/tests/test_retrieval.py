from app.services.retrieval_service import RetrievalService


def test_rrf_fusion():
    service = RetrievalService.__new__(RetrievalService)
    fused = service._rrf([("a", 0.9), ("b", 0.6)], [("b", 0.7), ("c", 0.5)])
    assert "a" in fused and "b" in fused and "c" in fused
    assert fused["b"] > 0
