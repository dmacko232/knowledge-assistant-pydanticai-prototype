"""Text preprocessing utilities."""

import re

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

# Download required NLTK data (will be cached after first run)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)

try:
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("wordnet", quiet=True)

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

# Initialize lemmatizer and stopwords
lemmatizer = WordNetLemmatizer()
STOP_WORDS = set(stopwords.words("english"))


def preprocess_for_embedding(text: str) -> str:
    """
    Preprocess text for embedding generation.

    - Remove special characters
    - Normalize whitespace
    - Keep the text readable for semantic understanding

    Args:
        text: Raw text to preprocess

    Returns:
        Preprocessed text suitable for embedding
    """
    # Remove markdown formatting but keep content
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # Remove links, keep text
    text = re.sub(r"[#*`_~]", "", text)  # Remove markdown formatting chars

    # Remove special characters but keep sentence structure
    text = re.sub(r"[^\w\s.,!?;:\-]", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def preprocess_for_fts5(text: str) -> str:
    """
    Preprocess text for FTS5 (Full-Text Search) indexing.

    - Tokenize
    - Lowercase
    - Remove stopwords
    - Lemmatize
    - Return space-separated tokens

    Args:
        text: Raw text to preprocess

    Returns:
        Preprocessed text as space-separated tokens
    """
    # Lowercase
    text = text.lower()

    # Remove special characters
    text = re.sub(r"[^\w\s]", " ", text)

    # Tokenize
    tokens = word_tokenize(text)

    # Remove stopwords and lemmatize
    tokens = [
        lemmatizer.lemmatize(token)
        for token in tokens
        if token not in STOP_WORDS and len(token) > 2
    ]

    return " ".join(tokens)


def extract_date_from_text(text: str) -> str | None:
    """
    Extract date from text in YYYY-MM-DD format.

    Looks for patterns like:
    - Last updated: 2026-01-12
    - Updated: 2026-01-12
    - Date: 2026-01-12

    Args:
        text: Text containing a date

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    # Look for common date patterns in first 500 chars
    first_part = text[:500]

    # Pattern: YYYY-MM-DD
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", first_part)
    if date_match:
        return date_match.group(0)

    return None


def count_tokens(text: str) -> int:
    """
    Count approximate tokens in text.

    Uses word tokenization as a proxy for token count.

    Args:
        text: Text to count tokens in

    Returns:
        Approximate token count
    """
    tokens = word_tokenize(text)
    return len(tokens)


if __name__ == "__main__":
    # Test the functions
    sample_text = """
    # KPI Definitions Overview

    Last updated: 2026-01-12

    This is a [test link](example.com) with **bold** text.
    """

    print("Original:", sample_text)
    print("\nFor embedding:", preprocess_for_embedding(sample_text))
    print("\nFor FTS5:", preprocess_for_fts5(sample_text))
    print("\nExtracted date:", extract_date_from_text(sample_text))
    print("\nToken count:", count_tokens(sample_text))
