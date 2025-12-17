"""
Grading logic for sentence builder exercises.
Uses normalized string equality.
"""
import unicodedata
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class GradeResult:
    """Result of grading a user's answer."""
    correct: bool
    user_answer_normalized: str
    expected_normalized: str
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "correct": self.correct,
            "your_answer": self.user_answer_normalized,
            "expected": self.expected_normalized,
        }


# Punctuation characters to strip from grading
PUNCTUATION_CHARS = set("。、．，.!?！？…・「」『』（）()【】〈〉《》")


def normalize_for_grading(text: str) -> str:
    """
    Normalize text for grading comparison.

    Applies:
    - NFKC Unicode normalization
    - Remove all whitespace (spaces, tabs, newlines)
    - Remove all punctuation
    """
    # NFKC normalization (handles full-width to half-width, etc.)
    text = unicodedata.normalize("NFKC", text)

    # Remove all whitespace
    text = re.sub(r'\s+', '', text)

    # Remove all punctuation
    text = "".join(c for c in text if c not in PUNCTUATION_CHARS)

    return text


def grade(user_answer: str, canonical_answer: str) -> GradeResult:
    """
    Grade a user's answer against the canonical answer.
    
    Args:
        user_answer: The user's submitted answer (concatenated tiles)
        canonical_answer: The expected correct answer
        
    Returns:
        GradeResult with correctness and normalized strings
    """
    user_normalized = normalize_for_grading(user_answer)
    expected_normalized = normalize_for_grading(canonical_answer)
    
    correct = user_normalized == expected_normalized
    
    return GradeResult(
        correct=correct,
        user_answer_normalized=user_normalized,
        expected_normalized=expected_normalized
    )


def grade_tiles(tiles: list, canonical_answer: str) -> GradeResult:
    """
    Grade a list of tile surfaces against the canonical answer.
    
    Args:
        tiles: List of tile surface strings in user's order
        canonical_answer: The expected correct answer
        
    Returns:
        GradeResult with correctness and normalized strings
    """
    user_answer = "".join(tiles)
    return grade(user_answer, canonical_answer)


if __name__ == "__main__":
    # Demo/test
    test_cases = [
        # (user_answer, canonical, expected_correct)
        ("私は猫が好きです。", "私は猫が好きです。", True),
        ("私 は 猫 が 好き です 。", "私は猫が好きです。", True),  # With spaces
        ("私は犬が好きです。", "私は猫が好きです。", False),  # Wrong word
        ("私は猫が好きです", "私は猫が好きです。", False),  # Missing period
        ("ワタシハネコガスキデス。", "私は猫が好きです。", False),  # Katakana
    ]
    
    print("Grade function tests:")
    for user, canonical, expected in test_cases:
        result = grade(user, canonical)
        status = "✓" if result.correct == expected else "✗"
        print(f"{status} '{user}' vs '{canonical}' -> {result.correct}")

