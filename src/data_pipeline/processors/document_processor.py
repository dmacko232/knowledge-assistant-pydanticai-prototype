"""Document processing for markdown files."""

import hashlib
from pathlib import Path

import config
from database.models import DocumentChunk
from utils.markdown_utils import chunk_by_structure, extract_metadata, parse_markdown_structure
from utils.text_utils import count_tokens, preprocess_for_embedding, preprocess_for_fts5


class DocumentProcessor:
    """Processes markdown documents into chunks ready for embedding."""

    def __init__(self):
        """Initialize document processor."""
        self.min_chunk_size = config.MIN_CHUNK_SIZE
        self.max_chunk_size = config.MAX_CHUNK_SIZE

    def process_document(
        self, file_path: Path, category: str
    ) -> tuple[list[DocumentChunk], list[str]]:
        """
        Process a single markdown document into chunks.

        Args:
            file_path: Path to markdown file
            category: Document category (domain/policies/runbooks)

        Returns:
            Tuple of (chunks, fts_contents) where:
            - chunks: List of DocumentChunk model instances
            - fts_contents: List of preprocessed text for FTS5 (same order as chunks)
        """
        # Read document
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Extract metadata
        metadata = extract_metadata(content)

        # Parse structure and chunk
        sections = parse_markdown_structure(content)
        raw_chunks = chunk_by_structure(sections, self.min_chunk_size, self.max_chunk_size)

        # Process each chunk
        processed_chunks = []
        fts_contents = []

        for i, chunk in enumerate(raw_chunks):
            chunk_id = self._generate_chunk_id(file_path.name, i)

            # Retrieval: strip markdown etc. for embedding (clean, normalized text)
            retrieval_chunk = preprocess_for_embedding(chunk["text"])

            # Generation: keep raw markdown (full section, no preprocessing)
            generation_chunk = chunk["section_full_text"]

            # Preprocess for FTS5
            fts_content = preprocess_for_fts5(chunk["text"])

            # Create DocumentChunk model instance
            doc_chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_name=file_path.name,
                category=category,
                section_header=chunk["section_header"],
                retrieval_chunk=retrieval_chunk,
                generation_chunk=generation_chunk,
                last_updated=metadata.last_updated,
                word_count=count_tokens(chunk["text"]),
                chunk_metadata={
                    "file_path": str(file_path),
                    "document_title": metadata.title,
                    "chunk_index": i,
                    "total_chunks": len(raw_chunks),
                    "sections": chunk["sections"],
                },
            )

            processed_chunks.append(doc_chunk)
            fts_contents.append(fts_content)

        return processed_chunks, fts_contents

    def process_all_documents(self) -> tuple[list[DocumentChunk], list[str]]:
        """
        Process all markdown documents in configured directories.

        Returns:
            Tuple of (all_chunks, all_fts_contents)
        """
        all_chunks = []
        all_fts_contents = []

        for category in config.DOCUMENT_CATEGORIES:
            category_dir = config.DOCUMENTS_DIR / category

            if not category_dir.exists():
                print(f"⚠ Category directory not found: {category_dir}")
                continue

            # Process all markdown files in category
            md_files = list(category_dir.glob("*.md"))
            print(f"Processing {len(md_files)} documents in '{category}'...")

            for md_file in md_files:
                try:
                    chunks, fts_contents = self.process_document(md_file, category)
                    all_chunks.extend(chunks)
                    all_fts_contents.extend(fts_contents)
                    print(f"  ✓ {md_file.name}: {len(chunks)} chunks")
                except Exception as e:
                    print(f"  ✗ Error processing {md_file.name}: {e}")

        return all_chunks, all_fts_contents

    def _generate_chunk_id(self, document_name: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_name}:{chunk_index}"
        hash_digest = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{document_name.replace('.md', '')}_{chunk_index}_{hash_digest}"


if __name__ == "__main__":
    # Test document processor
    processor = DocumentProcessor()

    # Test with a single document
    test_doc = config.DOCUMENTS_DIR / "domain" / "kpi_definitions_overview.md"
    if test_doc.exists():
        print(f"Testing with {test_doc.name}...")
        chunks, fts_contents = processor.process_document(test_doc, "domain")
        print(f"\n✓ Generated {len(chunks)} chunks")
        print("\nFirst chunk preview:")
        print(f"  ID: {chunks[0].chunk_id}")
        print(f"  Section: {chunks[0].section_header}")
        print(f"  Words: {chunks[0].word_count}")
        print(f"  Retrieval chunk: {chunks[0].retrieval_chunk[:100]}...")
    else:
        print(f"Test document not found: {test_doc}")
