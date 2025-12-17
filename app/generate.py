"""
Exercise generation: create tile-based exercises from sentence pairs.
"""
import os
import random
from dataclasses import dataclass, field
from typing import List, Set, Optional
from pathlib import Path

from .tokenize import Token, tokenize
from .dataset import Database, SentencePair, get_database


# Configuration
NUM_DISTRACTORS = int(os.environ.get("NUM_DISTRACTORS", "6"))
MAX_SENT_TOKENS = int(os.environ.get("MAX_SENT_TOKENS", "20"))
SEED = int(os.environ.get("SEED", "0")) if os.environ.get("SEED") else None

# POS categories for distractors
CONTENT_POS = {"名詞", "動詞", "形容詞", "形状詞", "副詞"}
# Punctuation to exclude from tiles
PUNCTUATION = {"。", "、", "．", "，", ".", ",", "！", "？", "!", "?", "…", "・",
               "「", "」", "『", "』", "（", "）", "(", ")", "【", "】", "〈", "〉", "《", "》"}


@dataclass
class Tile:
    """A tile in the word bank."""
    surface: str
    is_correct: bool
    token_index: Optional[int] = None  # Index in canonical answer, None for distractors


@dataclass
class Exercise:
    """A complete exercise with tiles and answer."""
    id: int
    english: str
    tiles: List[Tile]
    canonical_answer: str
    canonical_tokens: List[str]
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "exercise_id": self.id,
            "english": self.english,
            "tiles": [{"id": i, "text": t.surface} for i, t in enumerate(self.tiles)],
            "num_correct_tiles": len(self.canonical_tokens),
        }


def is_punctuation(surface: str) -> bool:
    """Check if surface is punctuation."""
    return surface in PUNCTUATION or all(c in PUNCTUATION for c in surface)


def is_content_word(token: Token) -> bool:
    """Check if token is a content word (noun, verb, adjective, etc.)."""
    return token.pos1 in CONTENT_POS


def create_exercise(
    sentence: SentencePair,
    db: Database,
    num_distractors: int = NUM_DISTRACTORS,
    seed: Optional[int] = None
) -> Optional[Exercise]:
    """
    Create an exercise from a sentence pair.
    
    Args:
        sentence: The sentence pair to create exercise from
        db: Database for distractor lookup
        num_distractors: Number of distractor tiles to add
        seed: Random seed for reproducibility
        
    Returns:
        Exercise object or None if sentence is unsuitable
    """
    if seed is not None:
        random.seed(seed)
    
    # Tokenize Japanese sentence
    tokens = tokenize(sentence.ja)

    # Skip if too many tokens
    if len(tokens) > MAX_SENT_TOKENS:
        return None

    if not tokens:
        return None

    # Filter out punctuation tokens for tiles (but keep for canonical answer)
    content_tokens = [t for t in tokens if not is_punctuation(t.surface)]

    if not content_tokens:
        return None

    # Build tiles from non-punctuation tokens
    canonical_surfaces = [t.surface for t in content_tokens]
    tiles = [Tile(surface=t.surface, is_correct=True, token_index=i)
             for i, t in enumerate(content_tokens)]

    # Collect surfaces already used (for distractor exclusion)
    used_surfaces: Set[str] = set(canonical_surfaces)

    # Add distractors for content words (nouns, verbs, adjectives, etc.)
    distractors_added = 0
    distractor_source_tokens = [(i, t) for i, t in enumerate(content_tokens) if is_content_word(t)]

    if distractor_source_tokens:
        distractors_per_token = max(1, num_distractors // len(distractor_source_tokens))

        for _, token in distractor_source_tokens:
            if distractors_added >= num_distractors:
                break
            
            # Get distractors of same POS and conjugation form
            distractor_surfaces = db.get_distractors(
                pos1=token.pos1,
                conj_form=token.conj_form,
                exclude=used_surfaces,
                limit=distractors_per_token
            )
            
            for surface in distractor_surfaces:
                if distractors_added >= num_distractors:
                    break
                tiles.append(Tile(surface=surface, is_correct=False))
                used_surfaces.add(surface)
                distractors_added += 1
    
    # Shuffle tiles for display
    random.shuffle(tiles)
    
    # Canonical answer is the normalized Japanese (for grading)
    canonical_answer = sentence.ja_norm
    
    return Exercise(
        id=sentence.id,
        english=sentence.en,
        tiles=tiles,
        canonical_answer=canonical_answer,
        canonical_tokens=canonical_surfaces
    )


def get_exercise(db: Optional[Database] = None, seed: Optional[int] = None) -> Optional[Exercise]:
    """
    Get a random exercise.
    
    Args:
        db: Database instance (uses default if None)
        seed: Random seed for reproducibility
        
    Returns:
        Exercise object or None if no sentences available
    """
    if db is None:
        db = get_database()
    
    effective_seed = seed if seed is not None else SEED
    
    # Get random sentence
    sentence = db.get_random_sentence(seed=effective_seed)
    if not sentence:
        return None
    
    return create_exercise(sentence, db, seed=effective_seed)


def get_exercise_by_id(sentence_id: int, db: Optional[Database] = None) -> Optional[Exercise]:
    """Get exercise for a specific sentence ID."""
    if db is None:
        db = get_database()
    
    sentence = db.get_sentence_by_id(sentence_id)
    if not sentence:
        return None
    
    return create_exercise(sentence, db)

