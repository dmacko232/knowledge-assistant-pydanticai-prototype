"""Unit tests for VectorStore."""

import pytest

from database.models import ChunkEmbedding, DocumentChunk, SearchResult
from database.vector_store import VectorStore


class TestVectorStore:
    """Test suite for VectorStore."""

    @pytest.fixture
    def store(self, temp_db_path):
        """Create a VectorStore instance."""
        store = VectorStore(temp_db_path)
        store.connect()
        store.create_tables()
        yield store
        store.close()

    def test_connect_and_create_tables(self, temp_db_path):
        """Test database connection and table creation."""
        store = VectorStore(temp_db_path)
        store.connect()

        assert store.engine is not None
        assert store.session is not None
        assert store.conn is not None

        store.create_tables()
        store.close()

    def test_insert_chunks(self, store):
        """Test inserting document chunks with embeddings."""
        # Create test chunks
        chunks = [
            DocumentChunk(
                chunk_id="test_chunk_1",
                document_name="test.md",
                category="domain",
                section_header="Test Section 1",
                retrieval_chunk="This is test content for retrieval",
                generation_chunk="This is test content for generation",
                word_count=6,
                chunk_metadata={"test": True},
            ),
            DocumentChunk(
                chunk_id="test_chunk_2",
                document_name="test.md",
                category="policies",
                section_header="Test Section 2",
                retrieval_chunk="Another test chunk",
                generation_chunk="Another test chunk with context",
                word_count=3,
                chunk_metadata={"test": True},
            ),
        ]

        embeddings = [
            ChunkEmbedding(chunk_id="test_chunk_1", embedding=[0.1] * 1536),
            ChunkEmbedding(chunk_id="test_chunk_2", embedding=[0.2] * 1536),
        ]

        fts_contents = ["test content retrieval", "another test chunk"]

        # Insert
        store.insert_chunks(chunks, embeddings, fts_contents)

        # Verify stats
        stats = store.get_stats()
        assert stats["total_chunks"] == 2
        assert stats["total_documents"] == 1

    def test_search_by_vector(self, store):
        """Test vector similarity search."""
        # Insert test data
        chunks = [
            DocumentChunk(
                chunk_id="chunk_1",
                document_name="doc1.md",
                category="domain",
                section_header="Section 1",
                retrieval_chunk="Data science and machine learning",
                generation_chunk="Data science and machine learning",
                word_count=5,
            ),
            DocumentChunk(
                chunk_id="chunk_2",
                document_name="doc1.md",
                category="domain",
                section_header="Section 2",
                retrieval_chunk="Policy documentation and guidelines",
                generation_chunk="Policy documentation and guidelines",
                word_count=4,
            ),
        ]

        embeddings = [
            ChunkEmbedding(chunk_id="chunk_1", embedding=[0.5] * 1536),
            ChunkEmbedding(chunk_id="chunk_2", embedding=[0.1] * 1536),
        ]

        fts_contents = ["data science machine learning", "policy documentation guidelines"]

        store.insert_chunks(chunks, embeddings, fts_contents)

        # Search (query embedding closer to chunk_1)
        query_embedding = [0.5] * 1536
        results = store.search_by_vector(query_embedding, limit=2)

        assert len(results) <= 2
        assert all(isinstance(chunk, SearchResult) for chunk in results)
        # First result should be chunk_1 (closer embedding)
        assert results[0].chunk_id == "chunk_1"

    def test_search_by_vector_with_category_filter(self, store):
        """Test vector search with category filter."""
        # Insert test data with different categories
        chunks = [
            DocumentChunk(
                chunk_id="chunk_1",
                document_name="doc1.md",
                category="domain",
                section_header="Section 1",
                retrieval_chunk="Domain knowledge",
                generation_chunk="Domain knowledge",
                word_count=2,
            ),
            DocumentChunk(
                chunk_id="chunk_2",
                document_name="doc2.md",
                category="policies",
                section_header="Section 2",
                retrieval_chunk="Policy rules",
                generation_chunk="Policy rules",
                word_count=2,
            ),
        ]

        embeddings = [
            ChunkEmbedding(chunk_id="chunk_1", embedding=[0.3] * 1536),
            ChunkEmbedding(chunk_id="chunk_2", embedding=[0.3] * 1536),
        ]

        fts_contents = ["domain knowledge", "policy rules"]

        store.insert_chunks(chunks, embeddings, fts_contents)

        # Search with category filter
        query_embedding = [0.3] * 1536
        results = store.search_by_vector(query_embedding, limit=10, category_filter="domain")

        assert len(results) == 1
        assert results[0].category == "domain"

    def test_search_by_bm25(self, store):
        """Test BM25 full-text search."""
        # Insert test data
        chunks = [
            DocumentChunk(
                chunk_id="chunk_1",
                document_name="doc1.md",
                category="domain",
                section_header="Machine Learning",
                retrieval_chunk="Machine learning models for prediction",
                generation_chunk="Machine learning models for prediction",
                word_count=5,
            ),
            DocumentChunk(
                chunk_id="chunk_2",
                document_name="doc1.md",
                category="domain",
                section_header="Data Science",
                retrieval_chunk="Data science best practices",
                generation_chunk="Data science best practices",
                word_count=4,
            ),
        ]

        embeddings = [
            ChunkEmbedding(chunk_id="chunk_1", embedding=[0.1] * 1536),
            ChunkEmbedding(chunk_id="chunk_2", embedding=[0.2] * 1536),
        ]

        fts_contents = ["machine learning models prediction", "data science best practices"]

        store.insert_chunks(chunks, embeddings, fts_contents)

        # Search for "machine learning"
        results = store.search_by_bm25("machine learning", limit=10)

        assert len(results) >= 1
        assert all(isinstance(chunk, SearchResult) for chunk in results)
        # Should find chunk with "machine learning"
        assert any("machine" in chunk.retrieval_chunk.lower() for chunk in results)

    def test_search_by_bm25_with_category_filter(self, store):
        """Test BM25 search with category filter."""
        # Insert test data
        chunks = [
            DocumentChunk(
                chunk_id="chunk_1",
                document_name="doc1.md",
                category="domain",
                section_header="Section 1",
                retrieval_chunk="Test content about policies",
                generation_chunk="Test content about policies",
                word_count=4,
            ),
            DocumentChunk(
                chunk_id="chunk_2",
                document_name="doc2.md",
                category="policies",
                section_header="Section 2",
                retrieval_chunk="Another test about policies",
                generation_chunk="Another test about policies",
                word_count=4,
            ),
        ]

        embeddings = [
            ChunkEmbedding(chunk_id="chunk_1", embedding=[0.1] * 1536),
            ChunkEmbedding(chunk_id="chunk_2", embedding=[0.2] * 1536),
        ]

        fts_contents = ["test content policies", "another test policies"]

        store.insert_chunks(chunks, embeddings, fts_contents)

        # Search with category filter
        results = store.search_by_bm25("policies", limit=10, category_filter="domain")

        assert len(results) == 1
        assert results[0].category == "domain"

    def test_get_stats(self, store):
        """Test getting statistics."""
        # Insert test data
        chunks = [
            DocumentChunk(
                chunk_id="chunk_1",
                document_name="doc1.md",
                category="domain",
                section_header="Section 1",
                retrieval_chunk="Content 1",
                generation_chunk="Content 1",
                word_count=2,
            ),
            DocumentChunk(
                chunk_id="chunk_2",
                document_name="doc1.md",
                category="domain",
                section_header="Section 2",
                retrieval_chunk="Content 2",
                generation_chunk="Content 2",
                word_count=2,
            ),
            DocumentChunk(
                chunk_id="chunk_3",
                document_name="doc2.md",
                category="policies",
                section_header="Section 3",
                retrieval_chunk="Content 3",
                generation_chunk="Content 3",
                word_count=2,
            ),
        ]

        embeddings = [
            ChunkEmbedding(chunk_id="chunk_1", embedding=[0.1] * 1536),
            ChunkEmbedding(chunk_id="chunk_2", embedding=[0.2] * 1536),
            ChunkEmbedding(chunk_id="chunk_3", embedding=[0.3] * 1536),
        ]

        fts_contents = ["content 1", "content 2", "content 3"]

        store.insert_chunks(chunks, embeddings, fts_contents)

        # Get stats
        stats = store.get_stats()
        assert stats["total_chunks"] == 3
        assert stats["total_documents"] == 2
        assert stats["by_category"]["domain"] == 2
        assert stats["by_category"]["policies"] == 1

    def test_reset(self, store):
        """Test resetting the database."""
        # Insert data
        chunk = DocumentChunk(
            chunk_id="test_chunk",
            document_name="test.md",
            category="domain",
            section_header="Test",
            retrieval_chunk="Test content",
            generation_chunk="Test content",
            word_count=2,
        )

        embedding = ChunkEmbedding(chunk_id="test_chunk", embedding=[0.1] * 1536)

        store.insert_chunks([chunk], [embedding], ["test content"])

        # Reset
        store.reset()

        # Recreate tables
        store.create_tables()

        # Verify data is gone
        stats = store.get_stats()
        assert stats["total_chunks"] == 0

    def test_insert_mismatched_lengths(self, store):
        """Test that inserting mismatched lengths raises an error."""
        chunks = [
            DocumentChunk(
                chunk_id="chunk_1",
                document_name="doc1.md",
                category="domain",
                section_header="Section 1",
                retrieval_chunk="Content",
                generation_chunk="Content",
                word_count=1,
            )
        ]

        embeddings = [
            ChunkEmbedding(chunk_id="chunk_1", embedding=[0.1] * 1536),
            ChunkEmbedding(chunk_id="chunk_2", embedding=[0.2] * 1536),
        ]

        fts_contents = ["content"]

        with pytest.raises(ValueError, match="must have the same length"):
            store.insert_chunks(chunks, embeddings, fts_contents)
