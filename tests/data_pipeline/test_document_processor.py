"""Unit tests for DocumentProcessor."""

import pytest

from database.models import DocumentChunk
from processors.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Test suite for DocumentProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance."""
        return DocumentProcessor()

    @pytest.fixture
    def sample_markdown(self, temp_dir):
        """Create a sample markdown file."""
        md_content = """---
title: Test Document
last_updated: 2026-01-15
---

# Introduction

This is the introduction section with some content.

## Section 1

This is section 1 with detailed information about the topic.

### Subsection 1.1

More detailed content in subsection 1.1.

## Section 2

This is section 2 with different content.
"""
        md_file = temp_dir / "test_doc.md"
        md_file.write_text(md_content)
        return md_file

    def test_process_document(self, processor, sample_markdown):
        """Test processing a single markdown document."""
        chunks, fts_contents = processor.process_document(sample_markdown, "domain")

        assert len(chunks) > 0
        assert len(chunks) == len(fts_contents)
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)

        # Check first chunk properties
        first_chunk = chunks[0]
        assert first_chunk.document_name == "test_doc.md"
        assert first_chunk.category == "domain"
        assert first_chunk.chunk_id is not None
        assert first_chunk.retrieval_chunk != ""
        assert first_chunk.generation_chunk != ""
        assert first_chunk.word_count > 0
        assert first_chunk.chunk_metadata is not None

    def test_chunk_id_generation(self, processor, sample_markdown):
        """Test that chunk IDs are unique and properly formatted."""
        chunks, _ = processor.process_document(sample_markdown, "domain")

        chunk_ids = [chunk.chunk_id for chunk in chunks]

        # All IDs should be unique
        assert len(chunk_ids) == len(set(chunk_ids))

        # IDs should contain document name (without .md) and index
        for i, chunk_id in enumerate(chunk_ids):
            assert "test_doc" in chunk_id
            assert str(i) in chunk_id

    def test_generation_chunk_is_full_section(self, processor, sample_markdown):
        """Test that generation chunk is always the full section (for context at generation)."""
        chunks, _ = processor.process_document(sample_markdown, "domain")

        for chunk in chunks:
            # Generation chunk must be the full section (raw), so it contains the section header
            assert chunk.section_header is None or chunk.section_header in chunk.generation_chunk
            assert len(chunk.generation_chunk) > 0

    def test_metadata_structure(self, processor, sample_markdown):
        """Test that metadata has the correct structure."""
        chunks, _ = processor.process_document(sample_markdown, "domain")

        for i, chunk in enumerate(chunks):
            assert "file_path" in chunk.chunk_metadata
            assert "document_title" in chunk.chunk_metadata
            assert "chunk_index" in chunk.chunk_metadata
            assert "total_chunks" in chunk.chunk_metadata
            assert "sections" in chunk.chunk_metadata

            assert chunk.chunk_metadata["chunk_index"] == i
            assert chunk.chunk_metadata["total_chunks"] == len(chunks)

    def test_fts_content_generation(self, processor, sample_markdown):
        """Test that FTS content is generated for each chunk."""
        chunks, fts_contents = processor.process_document(sample_markdown, "domain")

        assert len(fts_contents) == len(chunks)
        assert all(isinstance(content, str) for content in fts_contents)
        assert all(len(content) > 0 for content in fts_contents)

    def test_process_document_preserves_category(self, processor, sample_markdown):
        """Test that the category is correctly assigned to chunks."""
        # Test with different categories
        for category in ["domain", "policies", "runbooks"]:
            chunks, _ = processor.process_document(sample_markdown, category)
            assert all(chunk.category == category for chunk in chunks)

    def test_generate_chunk_id_consistency(self, processor):
        """Test that chunk ID generation is consistent."""
        doc_name = "test.md"
        index = 5

        # Generate ID twice
        id1 = processor._generate_chunk_id(doc_name, index)
        id2 = processor._generate_chunk_id(doc_name, index)

        # Should be identical
        assert id1 == id2

    def test_generate_chunk_id_uniqueness(self, processor):
        """Test that different inputs produce different chunk IDs."""
        doc_name = "test.md"

        id1 = processor._generate_chunk_id(doc_name, 0)
        id2 = processor._generate_chunk_id(doc_name, 1)
        id3 = processor._generate_chunk_id("other.md", 0)

        # All should be unique
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

    def test_process_document_empty_file(self, processor, temp_dir):
        """Test processing an empty markdown file."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")

        chunks, fts_contents = processor.process_document(empty_file, "domain")

        # Should handle empty file gracefully
        assert isinstance(chunks, list)
        assert isinstance(fts_contents, list)

    def test_process_document_with_metadata(self, processor, temp_dir):
        """Test processing document with frontmatter metadata."""
        md_content = """---
title: My Test Document
last_updated: 2026-01-20
---

# Content

Some content here.
"""
        md_file = temp_dir / "with_metadata.md"
        md_file.write_text(md_content)

        chunks, _ = processor.process_document(md_file, "domain")

        # Check that metadata is extracted
        assert len(chunks) > 0
        first_chunk = chunks[0]
        assert first_chunk.chunk_metadata["document_title"] is not None
        assert first_chunk.last_updated == "2026-01-20"

    def test_word_count_accuracy(self, processor, temp_dir):
        """Test that word count is reasonably accurate."""
        md_content = """# Test

This is a test document with exactly twenty words to verify the word count functionality works correctly for testing.
"""
        md_file = temp_dir / "word_count_test.md"
        md_file.write_text(md_content)

        chunks, _ = processor.process_document(md_file, "domain")

        assert len(chunks) > 0
        # Word count should be positive and reasonable
        for chunk in chunks:
            assert chunk.word_count > 0
            assert chunk.word_count < 1000  # Sanity check
