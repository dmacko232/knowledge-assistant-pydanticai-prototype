"""Vector storage with SQLite and sqlite-vec extension."""

import sqlite3
from pathlib import Path

import sqlite_vec
from sqlite_vec import serialize_float32
from sqlmodel import Session, SQLModel, create_engine, select

from database.interfaces import VectorStoreInterface
from database.models import ChunkEmbedding, DocumentChunk, SearchResult


class VectorStore(VectorStoreInterface):
    """Manages vector storage and search using SQLite with vec extension and FTS5."""

    def __init__(self, db_path: Path):
        """
        Initialize vector store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = None
        self.session: Session | None = None
        self.conn: sqlite3.Connection | None = None
        self.embedding_dim = 1536  # OpenAI text-embedding-3-small dimension

    def connect(self) -> None:
        """Connect to database and load extensions."""
        connection_string = f"sqlite:///{self.db_path}"
        self.engine = create_engine(connection_string, echo=False)
        self.session = Session(self.engine)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close database connection."""
        if self.session:
            self.session.close()
        if self.conn:
            self.conn.close()

    def create_tables(self) -> None:
        """Create tables for document chunks with vector and FTS5 support."""
        if not self.engine or not self.conn:
            raise RuntimeError("Database not connected. Call connect() first.")

        SQLModel.metadata.create_all(self.engine, tables=[DocumentChunk.__table__])

        cursor = self.conn.cursor()
        cursor.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                chunk_id TEXT PRIMARY KEY,
                embedding FLOAT[{self.embedding_dim}]
            )
        """)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                chunk_id UNINDEXED,
                document_name,
                category,
                section_header,
                content,
                tokenize='porter unicode61'
            )
        """)
        self.conn.commit()
        print("✓ Created vector store tables (document_chunks, vec_chunks, fts_chunks)")

    def insert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[ChunkEmbedding],
        fts_contents: list[str],
    ) -> None:
        """Insert document chunks with embeddings."""
        if not self.session or not self.conn:
            raise RuntimeError("Database not connected. Call connect() first.")

        if len(chunks) != len(embeddings) or len(chunks) != len(fts_contents):
            raise ValueError("chunks, embeddings, and fts_contents must have the same length")

        cursor = self.conn.cursor()
        for chunk, embedding, fts_content in zip(chunks, embeddings, fts_contents):
            self.session.add(chunk)
            cursor.execute(
                """
                INSERT INTO vec_chunks (chunk_id, embedding)
                VALUES (?, ?)
                """,
                (embedding.chunk_id, serialize_float32(embedding.embedding)),
            )
            cursor.execute(
                """
                INSERT INTO fts_chunks (
                    chunk_id, document_name, category, section_header, content
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    chunk.document_name,
                    chunk.category,
                    chunk.section_header,
                    fts_content,
                ),
            )
        self.conn.commit()
        self.session.commit()

    def search_by_vector(
        self,
        query_embedding: list[float],
        limit: int = 10,
        category_filter: str | None = None,
    ) -> list[SearchResult]:
        """Search chunks by vector similarity."""
        if not self.conn or not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        cursor = self.conn.cursor()
        if category_filter:
            query = """
                SELECT c.chunk_id, v.distance
                FROM vec_chunks v
                JOIN document_chunks c ON v.chunk_id = c.chunk_id
                WHERE c.category = ?
                    AND v.embedding MATCH ?
                    AND v.k = ?
                ORDER BY v.distance
            """
            cursor.execute(
                query,
                (category_filter, serialize_float32(query_embedding), limit),
            )
        else:
            query = """
                SELECT c.chunk_id, v.distance
                FROM vec_chunks v
                JOIN document_chunks c ON v.chunk_id = c.chunk_id
                WHERE v.embedding MATCH ?
                    AND v.k = ?
                ORDER BY v.distance
            """
            cursor.execute(query, (serialize_float32(query_embedding), limit))

        results = []
        for row in cursor.fetchall():
            chunk_id = row["chunk_id"]
            distance = row["distance"]
            chunk = self.session.exec(
                select(DocumentChunk).where(DocumentChunk.chunk_id == chunk_id)
            ).first()
            if chunk:
                result = SearchResult(
                    **chunk.model_dump(),
                    distance=distance,
                    score=1 / (1 + distance),
                )
                results.append(result)
        return results

    def search_by_bm25(
        self,
        query: str,
        limit: int = 10,
        category_filter: str | None = None,
    ) -> list[SearchResult]:
        """Search chunks using BM25 (FTS5 full-text search)."""
        if not self.conn or not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        cursor = self.conn.cursor()
        if category_filter:
            sql = """
                SELECT fts_chunks.chunk_id, bm25(fts_chunks) as bm25_score
                FROM fts_chunks
                JOIN document_chunks c ON fts_chunks.chunk_id = c.chunk_id
                WHERE fts_chunks MATCH ? AND c.category = ?
                ORDER BY bm25_score
                LIMIT ?
            """
            cursor.execute(sql, (query, category_filter, limit))
        else:
            sql = """
                SELECT fts_chunks.chunk_id, bm25(fts_chunks) as bm25_score
                FROM fts_chunks
                WHERE fts_chunks MATCH ?
                ORDER BY bm25_score
                LIMIT ?
            """
            cursor.execute(sql, (query, limit))

        results = []
        for row in cursor.fetchall():
            chunk_id = row["chunk_id"]
            bm25_score = row["bm25_score"]
            chunk = self.session.exec(
                select(DocumentChunk).where(DocumentChunk.chunk_id == chunk_id)
            ).first()
            if chunk:
                result = SearchResult(
                    **chunk.model_dump(),
                    bm25_score=bm25_score,
                )
                results.append(result)
        return results

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")

        total_chunks = len(self.session.exec(select(DocumentChunk)).all())
        by_category: dict[str, int] = {}
        for chunk in self.session.exec(select(DocumentChunk)).all():
            by_category[chunk.category] = by_category.get(chunk.category, 0) + 1
        total_documents = len(
            {c.document_name for c in self.session.exec(select(DocumentChunk)).all()}
        )
        return {
            "total_chunks": total_chunks,
            "total_documents": total_documents,
            "by_category": by_category,
        }

    def reset(self) -> None:
        """Drop all tables (use with caution)."""
        if not self.engine or not self.conn:
            raise RuntimeError("Database not connected. Call connect() first.")
        cursor = self.conn.cursor()
        SQLModel.metadata.drop_all(self.engine, tables=[DocumentChunk.__table__])
        cursor.execute("DROP TABLE IF EXISTS vec_chunks")
        cursor.execute("DROP TABLE IF EXISTS fts_chunks")
        self.conn.commit()
        print("✓ Dropped all vector store tables")
