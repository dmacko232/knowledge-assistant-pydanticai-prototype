"""Main CLI for running the data pipeline."""

import sys

import click

import config
from database.relational_store import RelationalStore
from database.vector_store import VectorStore
from processors.document_processor import DocumentProcessor
from processors.embedding_processor import EmbeddingProcessor
from processors.structured_processor import StructuredDataProcessor


@click.group()
def cli():
    """Data pipeline for Northwind Commerce knowledge assistant."""
    pass


@cli.command()
@click.option(
    "--mock-embeddings",
    is_flag=True,
    help="Use mock embeddings (no Azure API). Use for local DB creation without API keys.",
)
def process_all(mock_embeddings: bool):
    """Process all data (documents and structured data)."""
    click.echo("=" * 60)
    click.echo("Starting full data pipeline")
    click.echo("=" * 60)

    try:
        # Validate configuration
        click.echo("\n1. Validating configuration...")
        config.validate_config()

        # Process documents
        click.echo("\n2. Processing documents...")
        doc_processor = DocumentProcessor()
        chunks, fts_contents = doc_processor.process_all_documents()
        click.echo(f"   Total chunks created: {len(chunks)}")

        # Generate embeddings
        click.echo("\n3. Generating embeddings...")
        if mock_embeddings:
            from services.embedding_service import MockEmbeddingService

            embedding_processor = EmbeddingProcessor(embedding_service=MockEmbeddingService())
            click.echo("   (using mock embeddings)")
        else:
            embedding_processor = EmbeddingProcessor()
        chunks, embeddings = embedding_processor.generate_embeddings(chunks)

        # Store in vector database
        click.echo("\n4. Storing in vector database...")
        vector_store = VectorStore(config.DB_PATH)
        vector_store.connect()
        vector_store.create_tables()
        vector_store.insert_chunks(chunks, embeddings, fts_contents)

        # Get vector store stats
        stats = vector_store.get_stats()
        click.echo("   ✓ Vector store stats:")
        click.echo(f"     - Total chunks: {stats['total_chunks']}")
        click.echo(f"     - Total documents: {stats['total_documents']}")
        click.echo(f"     - By category: {stats['by_category']}")
        vector_store.close()

        # Process structured data
        click.echo("\n5. Processing structured data...")
        structured_processor = StructuredDataProcessor()

        # Process KPIs
        kpis = structured_processor.process_kpi_catalog()
        structured_processor.validate_kpi_data(kpis)

        # Process directory
        employees = structured_processor.process_directory()
        structured_processor.validate_directory_data(employees)

        # Store in relational database
        click.echo("\n6. Storing in relational database...")
        relational_store = RelationalStore(config.DB_PATH)
        relational_store.connect()
        relational_store.create_tables()
        relational_store.insert_kpis(kpis)
        relational_store.insert_employees(employees)

        # Get relational store stats
        rel_stats = relational_store.get_stats()
        click.echo("   ✓ Relational store stats:")
        click.echo(f"     - Total KPIs: {rel_stats['total_kpis']}")
        click.echo(f"     - Total employees: {rel_stats['total_employees']}")
        relational_store.close()

        # Summary
        click.echo("\n" + "=" * 60)
        click.echo("✓ Pipeline completed successfully!")
        click.echo("=" * 60)
        click.echo(f"Database: {config.DB_PATH}")

    except Exception as e:
        click.echo(f"\n✗ Pipeline failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--mock-embeddings",
    is_flag=True,
    help="Use mock embeddings (no Azure API).",
)
def process_documents(mock_embeddings: bool):
    """Process only documents (skip structured data)."""
    click.echo("Processing documents only...")

    try:
        config.validate_config()

        doc_processor = DocumentProcessor()
        chunks, fts_contents = doc_processor.process_all_documents()

        if mock_embeddings:
            from services.embedding_service import MockEmbeddingService

            embedding_processor = EmbeddingProcessor(embedding_service=MockEmbeddingService())
        else:
            embedding_processor = EmbeddingProcessor()
        chunks, embeddings = embedding_processor.generate_embeddings(chunks)

        vector_store = VectorStore(config.DB_PATH)
        vector_store.connect()
        vector_store.create_tables()
        vector_store.insert_chunks(chunks, embeddings, fts_contents)

        stats = vector_store.get_stats()
        click.echo(
            f"\n✓ Processed {stats['total_chunks']} chunks from {stats['total_documents']} documents"
        )
        vector_store.close()

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def process_structured():
    """Process only structured data (skip documents)."""
    click.echo("Processing structured data only...")

    try:
        config.validate_config()

        structured_processor = StructuredDataProcessor()

        kpis = structured_processor.process_kpi_catalog()
        structured_processor.validate_kpi_data(kpis)

        employees = structured_processor.process_directory()
        structured_processor.validate_directory_data(employees)

        relational_store = RelationalStore(config.DB_PATH)
        relational_store.connect()
        relational_store.create_tables()
        relational_store.insert_kpis(kpis)
        relational_store.insert_employees(employees)

        stats = relational_store.get_stats()
        click.echo(
            f"\n✓ Processed {stats['total_kpis']} KPIs and {stats['total_employees']} employees"
        )
        relational_store.close()

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def reset():
    """Reset databases (drop all tables)."""
    if not click.confirm("⚠ This will delete all data. Continue?"):
        click.echo("Cancelled.")
        return

    try:
        # Reset vector store
        if config.DB_PATH.exists():
            vector_store = VectorStore(config.DB_PATH)
            vector_store.connect()
            vector_store.reset()
            vector_store.close()

        # Reset relational store
        if config.DB_PATH.exists():
            relational_store = RelationalStore(config.DB_PATH)
            relational_store.connect()
            relational_store.reset()
            relational_store.close()

        click.echo("✓ Databases reset successfully")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--sample", default=3, help="Number of sample rows per table (0 to skip).")
@click.option("--schema", is_flag=True, help="Show CREATE TABLE for each table.")
def dump_db(sample: int, schema: bool):
    """Dump database contents: tables, row counts, and optional sample rows."""
    import sqlite3

    if not config.DB_PATH.exists():
        click.echo(f"✗ Database not found: {config.DB_PATH}", err=True)
        sys.exit(1)

    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # List tables (including virtual)
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name"
    )
    tables = [row[0] for row in cur.fetchall()]

    click.echo(f"Database: {config.DB_PATH}\n")
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM [{table}]")
            count = cur.fetchone()[0]
        except sqlite3.OperationalError:
            count = "?"
        click.echo(f"=== {table} (rows: {count}) ===")
        if schema:
            cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            row = cur.fetchone()
            if row and row[0]:
                click.echo(row[0][:500] + ("..." if len(row[0]) > 500 else ""))
        if sample and count and count != "?" and count > 0:
            cur.execute(f"SELECT * FROM [{table}] LIMIT {sample}")
            rows = cur.fetchall()
            for i, row in enumerate(rows, 1):
                click.echo(f"  --- row {i} ---")
                for key in row.keys():
                    val = row[key]
                    if val is None:
                        val = "NULL"
                    elif isinstance(val, bytes):
                        val = f"<bytes len={len(val)}>"
                    elif isinstance(val, str) and len(val) > 80:
                        val = val[:80] + "..."
                    click.echo(f"    {key}: {val}")
        click.echo("")

    conn.close()
    click.echo("Done.")


@cli.command()
def stats():
    """Show database statistics."""
    try:
        # Vector store stats
        if config.DB_PATH.exists():
            click.echo("Vector Store:")
            vector_store = VectorStore(config.DB_PATH)
            vector_store.connect()
            stats = vector_store.get_stats()
            click.echo(f"  Chunks: {stats['total_chunks']}")
            click.echo(f"  Documents: {stats['total_documents']}")
            click.echo(f"  By category: {stats['by_category']}")
            vector_store.close()
        else:
            click.echo("Vector Store: Not initialized")

        # Relational store stats
        if config.DB_PATH.exists():
            click.echo("\nRelational Store:")
            relational_store = RelationalStore(config.DB_PATH)
            relational_store.connect()
            stats = relational_store.get_stats()
            click.echo(f"  KPIs: {stats['total_kpis']}")
            click.echo(f"  Employees: {stats['total_employees']}")
            relational_store.close()
        else:
            click.echo("\nRelational Store: Not initialized")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--limit", default=5, help="Number of results to return")
@click.option("--category", default=None, help="Filter by category")
def search_vector(query, limit, category):
    """Search documents using vector similarity."""
    try:
        if not config.DB_PATH.exists():
            click.echo("✗ Vector database not found. Run 'process-all' first.", err=True)
            sys.exit(1)

        # Generate query embedding
        embedding_processor = EmbeddingProcessor()
        query_embedding = embedding_processor.generate_query_embedding(query)

        # Search
        vector_store = VectorStore(config.DB_PATH)
        vector_store.connect()
        results = vector_store.search_by_vector(query_embedding, limit, category)
        vector_store.close()

        # Display results
        click.echo(f"\nFound {len(results)} results for: '{query}'")
        for i, result in enumerate(results, 1):
            click.echo(f"\n{i}. {result.document_name} - {result.section_header}")
            click.echo(f"   Category: {result.category}")
            click.echo(f"   Score: {result.score:.4f}")
            click.echo(f"   Text: {result.retrieval_chunk[:200]}...")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--limit", default=5, help="Number of results to return")
@click.option("--category", default=None, help="Filter by category")
def search_bm25(query, limit, category):
    """Search documents using BM25 (keyword search)."""
    try:
        if not config.DB_PATH.exists():
            click.echo("✗ Vector database not found. Run 'process-all' first.", err=True)
            sys.exit(1)

        vector_store = VectorStore(config.DB_PATH)
        vector_store.connect()
        results = vector_store.search_by_bm25(query, limit, category)
        vector_store.close()

        # Display results
        click.echo(f"\nFound {len(results)} results for: '{query}'")
        for i, result in enumerate(results, 1):
            click.echo(f"\n{i}. {result.document_name} - {result.section_header}")
            click.echo(f"   Category: {result.category}")
            click.echo(f"   BM25 Score: {result.bm25_score:.4f}")
            click.echo(f"   Text: {result.retrieval_chunk[:200]}...")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
