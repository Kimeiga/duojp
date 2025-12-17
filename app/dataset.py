"""
SQLite database access for sentence pairs and token inventory.
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import random
import os

from .tokenize import Token


@dataclass
class SentencePair:
    """A sentence pair from the database."""
    id: int
    en: str
    ja: str
    ja_norm: str


class Database:
    """SQLite database wrapper for sentence pairs and token inventory."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        # Enable multi-threaded access
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ensure_token_table()
    
    def _ensure_token_table(self) -> None:
        """Create token inventory table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                surface TEXT NOT NULL,
                lemma TEXT,
                pos1 TEXT,
                pos2 TEXT,
                conj_type TEXT,
                conj_form TEXT,
                reading TEXT,
                frequency INTEGER DEFAULT 1,
                UNIQUE(surface, pos1, conj_form)
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_pos1 ON tokens(pos1)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_conj_form ON tokens(conj_form)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_frequency ON tokens(frequency DESC)")
        self.conn.commit()
    
    def get_sentence_count(self) -> int:
        """Get total number of sentences in database."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM sentences")
        return cursor.fetchone()[0]
    
    def get_random_sentence(self, seed: Optional[int] = None) -> Optional[SentencePair]:
        """Get a random sentence pair from the database."""
        if seed is not None:
            random.seed(seed)
        
        count = self.get_sentence_count()
        if count == 0:
            return None
        
        offset = random.randint(0, count - 1)
        cursor = self.conn.execute(
            "SELECT id, en, ja, ja_norm FROM sentences LIMIT 1 OFFSET ?",
            (offset,)
        )
        row = cursor.fetchone()
        if row:
            return SentencePair(
                id=row["id"],
                en=row["en"],
                ja=row["ja"],
                ja_norm=row["ja_norm"]
            )
        return None
    
    def get_sentence_by_id(self, sentence_id: int) -> Optional[SentencePair]:
        """Get a sentence pair by ID."""
        cursor = self.conn.execute(
            "SELECT id, en, ja, ja_norm FROM sentences WHERE id = ?",
            (sentence_id,)
        )
        row = cursor.fetchone()
        if row:
            return SentencePair(
                id=row["id"],
                en=row["en"],
                ja=row["ja"],
                ja_norm=row["ja_norm"]
            )
        return None
    
    def add_token(self, token: Token) -> None:
        """Add or update token in inventory."""
        try:
            self.conn.execute("""
                INSERT INTO tokens (surface, lemma, pos1, pos2, conj_type, conj_form, reading, frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(surface, pos1, conj_form) DO UPDATE SET frequency = frequency + 1
            """, (token.surface, token.lemma, token.pos1, token.pos2, 
                  token.conj_type, token.conj_form, token.reading))
        except sqlite3.Error:
            pass  # Ignore errors for robustness
    
    def get_distractors(self, pos1: str, conj_form: str, exclude: set, 
                        limit: int = 10) -> List[str]:
        """
        Get distractor surfaces for a given POS and conjugation form.
        Returns surfaces not in the exclude set, ordered by frequency.
        """
        placeholders = ",".join("?" * len(exclude)) if exclude else "''"
        query = f"""
            SELECT surface FROM tokens 
            WHERE pos1 = ? AND surface NOT IN ({placeholders})
        """
        params = [pos1] + list(exclude)
        
        # Prefer same conjugation form for verbs/adjectives
        if conj_form:
            query += " AND conj_form = ?"
            params.append(conj_form)
        
        query += " ORDER BY frequency DESC LIMIT ?"
        params.append(limit * 2)  # Get extra to sample from
        
        cursor = self.conn.execute(query, params)
        surfaces = [row[0] for row in cursor.fetchall()]
        
        # Shuffle and return requested number
        random.shuffle(surfaces)
        return surfaces[:limit]
    
    def commit(self) -> None:
        """Commit pending changes."""
        self.conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()


# Module-level database instance
_db: Optional[Database] = None


def get_database(db_path: Optional[Path] = None) -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        if db_path is None:
            db_path = Path(os.environ.get("DB_PATH", "data/app.db"))
        _db = Database(db_path)
    return _db


def set_database(db: Database) -> None:
    """Set the module-level database instance."""
    global _db
    _db = db

