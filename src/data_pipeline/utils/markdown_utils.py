"""Markdown parsing and chunking utilities."""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MarkdownSection:
    """Represents a section in a markdown document."""

    level: int  # Header level (1-6)
    title: str  # Header text
    content: str  # Section content (excluding header)
    start_line: int  # Line number where section starts
    end_line: int  # Line number where section ends


@dataclass
class DocumentMetadata:
    """Metadata extracted from a markdown document."""

    title: str
    last_updated: str | None
    total_lines: int
    total_words: int


def parse_markdown_structure(markdown_text: str) -> list[MarkdownSection]:
    """
    Parse markdown document into structured sections based on headers.

    Args:
        markdown_text: Raw markdown text

    Returns:
        List of MarkdownSection objects
    """
    lines = markdown_text.split("\n")
    sections = []
    current_section = None
    current_content = []

    for i, line in enumerate(lines):
        # Check if line is a header
        header_match = re.match(r"^(#{1,6})\s+(.+)$", line)

        if header_match:
            # Save previous section if exists
            if current_section is not None:
                current_section.content = "\n".join(current_content).strip()
                current_section.end_line = i - 1
                sections.append(current_section)

            # Start new section
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            current_section = MarkdownSection(
                level=level, title=title, content="", start_line=i, end_line=i
            )
            current_content = []
        else:
            # Add to current section content
            if current_section is not None:
                current_content.append(line)
            else:
                # Content before first header - create a special "preamble" section
                if not sections and line.strip():
                    if current_content or line.strip():
                        current_content.append(line)

    # Handle content before first header
    if not sections and current_content:
        sections.append(
            MarkdownSection(
                level=0,
                title="Preamble",
                content="\n".join(current_content).strip(),
                start_line=0,
                end_line=len(current_content) - 1,
            )
        )

    # Save last section
    if current_section is not None:
        current_section.content = "\n".join(current_content).strip()
        current_section.end_line = len(lines) - 1
        sections.append(current_section)

    return sections


def _section_to_markdown(section: MarkdownSection) -> str:
    """Render a section as markdown (header + content)."""
    if section.level > 0:
        return f"{'#' * section.level} {section.title}\n{section.content}".strip()
    return section.content.strip()


def chunk_by_structure(
    sections: list[MarkdownSection], min_tokens: int = 300, max_tokens: int = 500
) -> list[dict[str, Any]]:
    """
    Chunk markdown so each section is a separate unit.

    - One section → one DB chunk if it fits within max_tokens.
    - If a section exceeds max_tokens, it is split into multiple DB chunks (by paragraphs).
    - Each chunk dict includes section_full_text so generation always uses the whole section.

    Args:
        sections: List of MarkdownSection objects
        min_tokens: Minimum tokens per chunk (unused when not merging; kept for API)
        max_tokens: Maximum tokens per retrieval chunk

    Returns:
        List of chunk dicts with section_header, text (retrieval), sections, section_full_text (generation).
    """
    from .text_utils import count_tokens

    chunks: list[dict[str, Any]] = []

    for section in sections:
        section_header = section.title
        section_full_text = _section_to_markdown(section)
        section_tokens = count_tokens(section_full_text)

        if section_tokens <= max_tokens:
            # Whole section fits → one chunk
            chunks.append(
                {
                    "section_header": section_header,
                    "text": section_full_text,
                    "sections": [section.title],
                    "section_full_text": section_full_text,
                }
            )
            continue

        # Section too large → split by paragraphs; each sub-chunk shares same section_full_text
        paragraphs = [p.strip() for p in section.content.split("\n\n") if p.strip()]
        if not paragraphs:
            # Section has header only
            chunks.append(
                {
                    "section_header": section_header,
                    "text": section_full_text,
                    "sections": [section.title],
                    "section_full_text": section_full_text,
                }
            )
            continue

        acc: list[str] = []
        acc_tokens = count_tokens(f"{'#' * section.level} {section.title}\n")

        for para in paragraphs:
            para_tokens = count_tokens(para)

            if acc_tokens + para_tokens > max_tokens and acc:
                # Emit current accumulator as a retrieval chunk
                part_content = "\n\n".join(acc)
                part_text = (
                    f"{'#' * section.level} {section.title}\n{part_content}"
                    if section.level > 0
                    else part_content
                )
                chunks.append(
                    {
                        "section_header": section_header,
                        "text": part_text.strip(),
                        "sections": [section.title],
                        "section_full_text": section_full_text,
                    }
                )
                acc = []
                acc_tokens = count_tokens(f"{'#' * section.level} {section.title}\n")

            acc.append(para)
            acc_tokens += para_tokens

        if acc:
            part_content = "\n\n".join(acc)
            part_text = (
                f"{'#' * section.level} {section.title}\n{part_content}"
                if section.level > 0
                else part_content
            )
            chunks.append(
                {
                    "section_header": section_header,
                    "text": part_text.strip(),
                    "sections": [section.title],
                    "section_full_text": section_full_text,
                }
            )

    return chunks


def extract_metadata(markdown_text: str) -> DocumentMetadata:
    """
    Extract metadata from markdown document.

    Args:
        markdown_text: Raw markdown text

    Returns:
        DocumentMetadata object
    """
    from .text_utils import extract_date_from_text

    lines = markdown_text.split("\n")

    # Extract title (first H1 header)
    title = "Untitled"
    for line in lines[:10]:
        match = re.match(r"^#\s+(.+)$", line)
        if match:
            title = match.group(1).strip()
            break

    # Extract last updated date
    last_updated = extract_date_from_text(markdown_text)

    # Count lines and words
    total_lines = len(lines)
    total_words = len(markdown_text.split())

    return DocumentMetadata(
        title=title, last_updated=last_updated, total_lines=total_lines, total_words=total_words
    )


if __name__ == "__main__":
    # Test with sample markdown
    sample_md = """# KPI Definitions Overview

Last updated: 2026-01-12

## Introduction
This document provides an overview of KPI definitions.

## Source of truth
The authoritative catalog is `data/kpi_catalog.csv`.

### Important notes
- Dashboards must link to the KPI definition entry
- Names must match exactly

## KPI design principles
- Single owner team per KPI
- Primary source listed for every KPI
- Prefer stable business definitions
"""

    print("Testing markdown parsing...")
    sections = parse_markdown_structure(sample_md)
    print(f"\nFound {len(sections)} sections:")
    for s in sections:
        print(f"  Level {s.level}: {s.title} ({len(s.content)} chars)")

    print("\nChunking...")
    chunks = chunk_by_structure(sections, min_tokens=20, max_tokens=50)
    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\n  Chunk {i + 1}: {chunk['section_header']}")
        print(f"  Text preview: {chunk['text'][:100]}...")

    print("\nMetadata:")
    metadata = extract_metadata(sample_md)
    print(f"  Title: {metadata.title}")
    print(f"  Last updated: {metadata.last_updated}")
    print(f"  Lines: {metadata.total_lines}, Words: {metadata.total_words}")
