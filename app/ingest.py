"""
Ingest OPUS Tatoeba EN-JA TSV data into SQLite database.
Handles normalization, quality filtering, and deduplication.
"""
import argparse
import csv
import gzip
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Iterator, Tuple, Optional

# Quality filter thresholds
MAX_CHARS = 200
MIN_CHARS = 2
MAX_ASCII_RATIO = 0.5  # For Japanese text


def normalize_japanese(text: str) -> str:
    """Normalize Japanese text using NFKC normalization."""
    return unicodedata.normalize("NFKC", text)


def has_url(text: str) -> bool:
    """Check if text contains a URL."""
    url_pattern = r'https?://|www\.|\.com|\.org|\.net|\.jp'
    return bool(re.search(url_pattern, text, re.IGNORECASE))


def ascii_ratio(text: str) -> float:
    """Calculate the ratio of ASCII characters in text."""
    if not text:
        return 0.0
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return ascii_count / len(text)


def is_valid_sentence(en: str, ja: str) -> bool:
    """Apply quality filters to sentence pair."""
    # Check lengths
    if len(en) < MIN_CHARS or len(ja) < MIN_CHARS:
        return False
    if len(en) > MAX_CHARS or len(ja) > MAX_CHARS:
        return False
    
    # Check for empty after strip
    if not en.strip() or not ja.strip():
        return False
    
    # Check for URLs
    if has_url(en) or has_url(ja):
        return False
    
    # Check ASCII ratio in Japanese (should be mostly Japanese characters)
    if ascii_ratio(ja) > MAX_ASCII_RATIO:
        return False
    
    return True


def read_tsv(filepath: Path) -> Iterator[Tuple[str, str]]:
    """
    Read TSV file (optionally gzipped) and yield (en, ja) pairs.
    Handles OPUS format which may have extra columns.
    """
    opener = gzip.open if filepath.suffix == '.gz' else open
    
    with opener(filepath, 'rt', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) >= 2:
                en, ja = row[0].strip(), row[1].strip()
                yield en, ja


def create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            en TEXT NOT NULL,
            ja TEXT NOT NULL,
            ja_norm TEXT NOT NULL,
            UNIQUE(en, ja_norm)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ja_norm ON sentences(ja_norm)")
    conn.commit()


def ingest_tsv(tsv_path: Path, db_path: Path, verbose: bool = False) -> dict:
    """
    Ingest TSV file into SQLite database.
    
    Returns:
        Dict with ingestion statistics
    """
    stats = {
        "total": 0,
        "filtered": 0,
        "duplicates": 0,
        "inserted": 0,
    }
    
    conn = sqlite3.connect(db_path)
    create_schema(conn)
    
    for en, ja in read_tsv(tsv_path):
        stats["total"] += 1
        
        # Quality filter
        if not is_valid_sentence(en, ja):
            stats["filtered"] += 1
            continue
        
        ja_norm = normalize_japanese(ja)
        
        try:
            conn.execute(
                "INSERT INTO sentences (en, ja, ja_norm) VALUES (?, ?, ?)",
                (en, ja, ja_norm)
            )
            stats["inserted"] += 1
        except sqlite3.IntegrityError:
            stats["duplicates"] += 1
        
        if verbose and stats["total"] % 10000 == 0:
            print(f"Processed {stats['total']} rows...")
    
    conn.commit()
    conn.close()
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Ingest Tatoeba EN-JA TSV into SQLite")
    parser.add_argument("--tsv", type=Path, required=True, help="Path to TSV file (can be .gz)")
    parser.add_argument("--db", type=Path, default=Path("data/app.db"), help="Output SQLite database")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not args.tsv.exists():
        print(f"Error: TSV file not found: {args.tsv}")
        return 1
    
    # Ensure output directory exists
    args.db.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Ingesting {args.tsv} -> {args.db}")
    stats = ingest_tsv(args.tsv, args.db, verbose=args.verbose)
    
    print(f"\nIngestion complete:")
    print(f"  Total rows:    {stats['total']}")
    print(f"  Filtered out:  {stats['filtered']}")
    print(f"  Duplicates:    {stats['duplicates']}")
    print(f"  Inserted:      {stats['inserted']}")
    
    return 0


if __name__ == "__main__":
    exit(main())

