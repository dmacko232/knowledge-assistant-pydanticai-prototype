"""Embedding generation processor using the embedding service."""

import time

from database.models import ChunkEmbedding, DocumentChunk
from services.embedding_service import IEmbeddingService, OpenAIEmbeddingService


class EmbeddingProcessor:
    """Generates embeddings using the embedding service."""

    def __init__(self, embedding_service: IEmbeddingService | None = None):
        """
        Initialize embedding processor.

        Args:
            embedding_service: Embedding service implementation (defaults to OpenAI)
        """
        self.embedding_service = embedding_service or OpenAIEmbeddingService()
        self.batch_size = 100  # Process in batches for efficiency

    def generate_embeddings(
        self, chunks: list[DocumentChunk]
    ) -> tuple[list[DocumentChunk], list[ChunkEmbedding]]:
        """
        Generate embeddings for document chunks.

        Args:
            chunks: List of DocumentChunk model instances

        Returns:
            Tuple of (chunks, embeddings)
        """
        print(f"Generating embeddings for {len(chunks)} chunks...")

        # Extract texts for embedding
        texts = [chunk.retrieval_chunk for chunk in chunks]

        # Generate embeddings in batch
        try:
            start_time = time.time()
            embedding_vectors = self.embedding_service.embed_batch(
                texts, batch_size=self.batch_size
            )
            elapsed = time.time() - start_time

            # Create ChunkEmbedding instances
            embeddings = []
            for chunk, embedding_vector in zip(chunks, embedding_vectors):
                chunk_embedding = ChunkEmbedding(
                    chunk_id=chunk.chunk_id, embedding=embedding_vector
                )
                embeddings.append(chunk_embedding)

            # Estimate cost (text-embedding-3-small: $0.02 per 1M tokens)
            total_tokens = sum(len(text.split()) * 1.3 for text in texts)  # Rough estimate
            estimated_cost = (total_tokens / 1_000_000) * 0.02

            print("✓ Embedding generation complete")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Estimated cost: ${estimated_cost:.4f}")

            return chunks, embeddings

        except Exception as e:
            print(f"✗ Error generating embeddings: {e}")
            raise

    def generate_query_embedding(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            Embedding vector
        """
        return self.embedding_service.embed_text(query)


if __name__ == "__main__":
    # Test embedding processor
    import config
    from database.models import DocumentChunk

    if not (config.AZURE_OPENAI_EMBEDDING_API_KEY or config.AZURE_OPENAI_API_KEY):
        print(
            "⚠ No Azure OpenAI API key set. Set AZURE_OPENAI_API_KEY or AZURE_OPENAI_EMBEDDING_API_KEY in .env"
        )
    else:
        processor = EmbeddingProcessor()

        # Test with sample chunks
        test_chunks = [
            DocumentChunk(
                chunk_id="test_1",
                document_name="test.md",
                category="domain",
                retrieval_chunk="This is a test document about KPI definitions.",
                generation_chunk="This is a test document about KPI definitions.",
                word_count=8,
            ),
            DocumentChunk(
                chunk_id="test_2",
                document_name="test.md",
                category="domain",
                retrieval_chunk="Another test chunk about employee directory.",
                generation_chunk="Another test chunk about employee directory.",
                word_count=6,
            ),
        ]

        print("Testing embedding generation...")
        chunks, embeddings = processor.generate_embeddings(test_chunks)

        print("\n✓ Generated embeddings:")
        for chunk, embedding in zip(chunks, embeddings):
            print(f"  {chunk.chunk_id}: {len(embedding.embedding)} dimensions")
            print(f"    First 5 values: {embedding.embedding[:5]}")
