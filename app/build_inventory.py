"""
Build token frequency inventory from ingested sentences.
This improves distractor quality by providing same-POS alternatives.
"""
import argparse
from pathlib import Path

from .dataset import Database
from .tokenize import tokenize


def build_inventory(db: Database, verbose: bool = False) -> dict:
    """
    Build token inventory from all sentences in database.
    
    Returns:
        Dict with build statistics
    """
    stats = {
        "sentences_processed": 0,
        "tokens_added": 0,
    }
    
    # Get all sentences
    cursor = db.conn.execute("SELECT id, ja FROM sentences")
    
    for row in cursor:
        sentence_id, ja = row
        stats["sentences_processed"] += 1
        
        try:
            tokens = tokenize(ja)
            for token in tokens:
                db.add_token(token)
                stats["tokens_added"] += 1
        except Exception as e:
            if verbose:
                print(f"Error tokenizing sentence {sentence_id}: {e}")
        
        if verbose and stats["sentences_processed"] % 1000 == 0:
            print(f"Processed {stats['sentences_processed']} sentences...")
    
    db.commit()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Build token frequency inventory")
    parser.add_argument("--db", type=Path, default=Path("data/app.db"), help="SQLite database path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not args.db.exists():
        print(f"Error: Database not found: {args.db}")
        print("Run ingestion first: python -m app.ingest --tsv data/tatoeba_en_ja.tsv --db data/app.db")
        return 1
    
    db = Database(args.db)
    
    print(f"Building token inventory from {args.db}...")
    stats = build_inventory(db, verbose=args.verbose)
    
    print(f"\nInventory build complete:")
    print(f"  Sentences processed: {stats['sentences_processed']}")
    print(f"  Tokens added/updated: {stats['tokens_added']}")
    
    # Show token count
    cursor = db.conn.execute("SELECT COUNT(*) FROM tokens")
    token_count = cursor.fetchone()[0]
    print(f"  Unique tokens in inventory: {token_count}")
    
    db.close()
    return 0


if __name__ == "__main__":
    exit(main())

