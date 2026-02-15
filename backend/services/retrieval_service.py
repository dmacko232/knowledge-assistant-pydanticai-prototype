"""Hybrid retrieval service combining vector search and BM25 with RRF reranking."""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import sqlite_vec
from openai import AzureOpenAI
from sqlite_vec import serialize_float32

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieval result with source metadata."""

    chunk_id: str
    document_name: str
    category: str
    section_header: str | None
    generation_chunk: str
    last_updated: str | None
    score: float
    chunk_metadata: dict = field(default_factory=dict)


class RetrievalService:
    """Performs hybrid search (vector + BM25) with Reciprocal Rank Fusion reranking.

    Optionally runs a cross-encoder reranker on the fused candidates when
    ``reranker_enabled=True`` and an API key is provided.
    """

    def __init__(
        self,
        db_path: Path,
        embedding_client: AzureOpenAI,
        embedding_deployment: str,
        embedding_dimensions: int = 1536,
        *,
        reranker_enabled: bool = False,
        reranker_api_key: str | None = None,
        reranker_model: str = "rerank-v3.5",
        reranker_top_n: int = 5,
    ):
        self.db_path = db_path
        self.embedding_client = embedding_client
        self.embedding_deployment = embedding_deployment
        self.embedding_dimensions = embedding_dimensions
        self.conn: sqlite3.Connection | None = None

        # Reranker config
        self.reranker_enabled = reranker_enabled
        self.reranker_api_key = reranker_api_key
        self.reranker_model = reranker_model
        self.reranker_top_n = reranker_top_n

        if self.reranker_enabled:
            logger.info("Reranker enabled (model=%s, top_n=%d)", reranker_model, reranker_top_n)
        else:
            logger.info("Reranker disabled — using RRF scores only")

    def connect(self) -> None:
        """Connect to the SQLite database and load the vector extension."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding vector for a query string."""
        response = self.embedding_client.embeddings.create(
            input=text,
            model=self.embedding_deployment,
            dimensions=self.embedding_dimensions,
        )
        return [float(x) for x in response.data[0].embedding]

    # ------------------------------------------------------------------
    # Individual search methods
    # ------------------------------------------------------------------

    def _vector_search(
        self,
        query_embedding: list[float],
        limit: int,
        category: str | None,
    ) -> list[tuple[str, float]]:
        """Search by vector similarity. Returns (chunk_id, distance) pairs."""
        if not self.conn:
            raise RuntimeError("Not connected")

        cursor = self.conn.cursor()
        if category:
            cursor.execute(
                """
                SELECT c.chunk_id, v.distance
                FROM vec_chunks v
                JOIN document_chunks c ON v.chunk_id = c.chunk_id
                WHERE c.category = ? AND v.embedding MATCH ? AND v.k = ?
                ORDER BY v.distance
                """,
                (category, serialize_float32(query_embedding), limit),
            )
        else:
            cursor.execute(
                """
                SELECT c.chunk_id, v.distance
                FROM vec_chunks v
                JOIN document_chunks c ON v.chunk_id = c.chunk_id
                WHERE v.embedding MATCH ? AND v.k = ?
                ORDER BY v.distance
                """,
                (serialize_float32(query_embedding), limit),
            )
        return [(row["chunk_id"], row["distance"]) for row in cursor.fetchall()]

    def _bm25_search(
        self,
        query: str,
        limit: int,
        category: str | None,
    ) -> list[tuple[str, float]]:
        """Search by BM25 full-text ranking. Returns (chunk_id, bm25_score) pairs."""
        if not self.conn:
            raise RuntimeError("Not connected")

        cursor = self.conn.cursor()
        if category:
            cursor.execute(
                """
                SELECT fts_chunks.chunk_id, bm25(fts_chunks) AS bm25_score
                FROM fts_chunks
                JOIN document_chunks c ON fts_chunks.chunk_id = c.chunk_id
                WHERE fts_chunks MATCH ? AND c.category = ?
                ORDER BY bm25_score
                LIMIT ?
                """,
                (query, category, limit),
            )
        else:
            cursor.execute(
                """
                SELECT fts_chunks.chunk_id, bm25(fts_chunks) AS bm25_score
                FROM fts_chunks
                WHERE fts_chunks MATCH ?
                ORDER BY bm25_score
                LIMIT ?
                """,
                (query, limit),
            )
        return [(row["chunk_id"], row["bm25_score"]) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Chunk detail lookup
    # ------------------------------------------------------------------

    def _get_chunk_details(self, chunk_id: str) -> dict | None:
        """Fetch full chunk data by chunk_id."""
        if not self.conn:
            raise RuntimeError("Not connected")

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT chunk_id, document_name, category, section_header,
                   generation_chunk, last_updated, chunk_metadata
            FROM document_chunks
            WHERE chunk_id = ?
            """,
            (chunk_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Reciprocal Rank Fusion
    # ------------------------------------------------------------------

    @staticmethod
    def reciprocal_rank_fusion(
        vector_results: list[tuple[str, float]],
        bm25_results: list[tuple[str, float]],
        k: int = 60,
    ) -> list[tuple[str, float]]:
        """Combine two ranked lists using RRF.

        Args:
            vector_results: (chunk_id, distance) from vector search, sorted ascending.
            bm25_results: (chunk_id, bm25_score) from BM25 search, sorted ascending.
            k: RRF smoothing constant (default 60).

        Returns:
            List of (chunk_id, rrf_score) sorted descending by score.
        """
        scores: dict[str, float] = {}
        for rank, (chunk_id, _) in enumerate(vector_results):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)
        for rank, (chunk_id, _) in enumerate(bm25_results):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # ------------------------------------------------------------------
    # Optional reranker
    # ------------------------------------------------------------------

    def _rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Re-score candidates using a cross-encoder reranker API.

        If the reranker is disabled or unavailable, returns candidates unchanged.
        Currently supports Cohere-compatible rerank APIs.  Swap the implementation
        for Azure AI, Jina, or a local cross-encoder as needed.
        """
        if not self.reranker_enabled or not self.reranker_api_key:
            return candidates

        if not candidates:
            return candidates

        try:
            import cohere

            client = cohere.Client(api_key=self.reranker_api_key)
            docs = [c.generation_chunk for c in candidates]
            response = client.rerank(
                model=self.reranker_model,
                query=query,
                documents=docs,
                top_n=self.reranker_top_n,
            )
            reranked: list[RetrievalResult] = []
            for hit in response.results:
                result = candidates[hit.index]
                result.score = hit.relevance_score
                reranked.append(result)
            logger.info("Reranker returned %d results", len(reranked))
            return reranked

        except ImportError:
            logger.warning(
                "Reranker enabled but 'cohere' package not installed. "
                "Install it with: pip install cohere"
            )
            return candidates
        except Exception:
            logger.exception("Reranker failed — falling back to RRF ordering")
            return candidates

    # ------------------------------------------------------------------
    # Public search API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        category: str | None = None,
        vector_limit: int = 10,
        bm25_limit: int = 10,
        final_limit: int = 5,
        rrf_k: int = 60,
    ) -> list[RetrievalResult]:
        """Run hybrid search: embed → vector + BM25 → RRF merge → (rerank) → top results.

        Args:
            query: The user's search query.
            category: Optional category filter ('domain', 'policies', 'runbooks').
            vector_limit: How many vector results to fetch.
            bm25_limit: How many BM25 results to fetch.
            final_limit: How many final results to return after fusion.
            rrf_k: RRF smoothing constant.

        Returns:
            List of RetrievalResult, ordered by relevance.
        """
        # 1) Embed the query
        query_embedding = self.embed_query(query)

        # 2) Vector search
        vector_results = self._vector_search(query_embedding, vector_limit, category)

        # 3) BM25 search (gracefully handle FTS5 syntax errors)
        try:
            bm25_results = self._bm25_search(query, bm25_limit, category)
        except Exception:
            bm25_results = []

        # 4) Fuse with RRF
        # When reranker is enabled, fetch more candidates so the reranker has a
        # richer pool to re-score.
        rrf_limit = max(final_limit, self.reranker_top_n * 2) if self.reranker_enabled else final_limit
        fused = self.reciprocal_rank_fusion(vector_results, bm25_results, k=rrf_k)

        # 5) Fetch chunk details for top candidates
        candidates: list[RetrievalResult] = []
        for chunk_id, score in fused[:rrf_limit]:
            details = self._get_chunk_details(chunk_id)
            if details:
                metadata = details.get("chunk_metadata") or {}
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}

                candidates.append(
                    RetrievalResult(
                        chunk_id=details["chunk_id"],
                        document_name=details["document_name"],
                        category=details["category"],
                        section_header=details["section_header"],
                        generation_chunk=details["generation_chunk"],
                        last_updated=details["last_updated"],
                        score=score,
                        chunk_metadata=metadata,
                    )
                )

        # 6) Optional reranker pass
        if self.reranker_enabled:
            candidates = self._rerank(query, candidates)
            candidates = candidates[:final_limit]

        return candidates
