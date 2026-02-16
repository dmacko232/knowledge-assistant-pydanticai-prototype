"""Tests for the retrieval service."""

import sqlite3
from pathlib import Path

import pytest

from domain.infrastructure.retrieval_service import RetrievalService
from domain.models import RetrievalResult


class TestReciprocalRankFusion:
    """Test the RRF algorithm independently (no DB or embedding needed)."""

    def test_single_source(self):
        vector = [("a", 0.1), ("b", 0.3), ("c", 0.5)]
        bm25: list[tuple[str, float]] = []
        fused = RetrievalService.reciprocal_rank_fusion(vector, bm25, k=60)

        ids = [cid for cid, _ in fused]
        assert ids == ["a", "b", "c"]  # order preserved

    def test_both_sources_boost_overlapping(self):
        vector = [("a", 0.1), ("b", 0.3), ("c", 0.5)]
        bm25 = [("b", -5.0), ("d", -3.0), ("a", -2.0)]
        fused = RetrievalService.reciprocal_rank_fusion(vector, bm25, k=60)

        scores = dict(fused)
        # "a" and "b" appear in both lists, so they should have higher scores
        assert scores["a"] > scores["c"]
        assert scores["b"] > scores["d"]

    def test_empty_both(self):
        fused = RetrievalService.reciprocal_rank_fusion([], [], k=60)
        assert fused == []

    def test_returns_descending_scores(self):
        vector = [("x", 0.1), ("y", 0.2)]
        bm25 = [("y", -5.0), ("z", -3.0)]
        fused = RetrievalService.reciprocal_rank_fusion(vector, bm25, k=60)
        scores = [s for _, s in fused]
        assert scores == sorted(scores, reverse=True)


class TestRetrievalResultDataclass:
    """Test the RetrievalResult dataclass."""

    def test_creation(self):
        r = RetrievalResult(
            chunk_id="c1",
            document_name="doc.md",
            category="domain",
            section_header="Intro",
            generation_chunk="Some content",
            last_updated="2025-01-01",
            score=0.85,
        )
        assert r.chunk_id == "c1"
        assert r.score == 0.85
        assert r.chunk_metadata == {}

    def test_with_metadata(self):
        r = RetrievalResult(
            chunk_id="c2",
            document_name="doc.md",
            category="policies",
            section_header=None,
            generation_chunk="Content",
            last_updated=None,
            score=0.5,
            chunk_metadata={"version": "v2"},
        )
        assert r.chunk_metadata == {"version": "v2"}


class TestChunkDetailLookup:
    """Test _get_chunk_details from a temporary database (no vec extension needed)."""

    @pytest.fixture()
    def retrieval_svc(self, tmp_vector_db: Path):
        """A RetrievalService with only the plain SQLite connection (no vec)."""
        svc = RetrievalService.__new__(RetrievalService)
        svc.db_path = tmp_vector_db
        svc.conn = sqlite3.connect(str(tmp_vector_db))
        svc.conn.row_factory = sqlite3.Row
        svc.embedding_client = None  # type: ignore[assignment]
        svc.embedding_deployment = ""
        svc.embedding_dimensions = 1536
        svc.reranker_enabled = False
        svc.reranker_api_key = None
        svc.reranker_model = ""
        svc.reranker_top_n = 5
        yield svc
        svc.conn.close()

    def test_get_existing_chunk(self, retrieval_svc: RetrievalService):
        details = retrieval_svc._get_chunk_details("chunk_1")
        assert details is not None
        assert details["document_name"] == "security_policy_v2.md"
        assert details["category"] == "policies"

    def test_get_nonexistent_chunk(self, retrieval_svc: RetrievalService):
        details = retrieval_svc._get_chunk_details("nonexistent")
        assert details is None


class TestRerankerDisabled:
    """Test that the reranker is a no-op when disabled."""

    def test_rerank_passthrough_when_disabled(self):
        svc = RetrievalService.__new__(RetrievalService)
        svc.reranker_enabled = False
        svc.reranker_api_key = None

        candidates = [
            RetrievalResult(
                chunk_id="c1",
                document_name="d.md",
                category="domain",
                section_header=None,
                generation_chunk="text",
                last_updated=None,
                score=0.9,
            ),
        ]
        result = svc._rerank("test query", candidates)
        assert result is candidates  # same object, untouched
