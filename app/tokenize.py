"""
MeCab + UniDic tokenization wrapper for Japanese text.
Supports unidic-lite by default, with option to use full UniDic.
"""
from dataclasses import dataclass
from typing import List, Optional
import MeCab
import os


@dataclass
class Token:
    """Represents a tokenized Japanese morpheme with UniDic features."""
    surface: str
    lemma: str
    pos1: str
    pos2: str
    pos3: str
    pos4: str
    conj_type: str
    conj_form: str
    reading: str
    pronunciation: str


def get_unidic_dir() -> Optional[str]:
    """
    Get UniDic dictionary directory.
    First tries unidic-lite, then falls back to system UniDic.
    """
    try:
        import unidic_lite
        return unidic_lite.DICDIR
    except ImportError:
        pass
    
    try:
        import unidic
        return unidic.DICDIR
    except ImportError:
        pass
    
    # Fall back to system default (empty string lets MeCab use default)
    return None


class Tokenizer:
    """MeCab tokenizer with UniDic dictionary."""
    
    def __init__(self, dicdir: Optional[str] = None):
        """
        Initialize the tokenizer.
        
        Args:
            dicdir: Path to UniDic dictionary directory. 
                    If None, auto-detects unidic-lite or system UniDic.
        """
        if dicdir is None:
            dicdir = get_unidic_dir()
        
        if dicdir:
            self.tagger = MeCab.Tagger(f"-d {dicdir}")
        else:
            self.tagger = MeCab.Tagger()
        
        # Workaround for MeCab GC bug - parse empty string first
        self.tagger.parse("")
    
    def tokenize(self, sentence: str) -> List[Token]:
        """
        Tokenize a Japanese sentence into morphemes.
        
        Args:
            sentence: Japanese text to tokenize
            
        Returns:
            List of Token objects with morphological information
        """
        tokens = []
        node = self.tagger.parseToNode(sentence)
        
        while node:
            # Skip BOS/EOS nodes (empty surface)
            if node.surface:
                features = node.feature.split(",")
                # UniDic typically has 17+ features, but guard for shorter
                token = Token(
                    surface=node.surface,
                    lemma=self._get_feature(features, 7, node.surface),
                    pos1=self._get_feature(features, 0, ""),
                    pos2=self._get_feature(features, 1, ""),
                    pos3=self._get_feature(features, 2, ""),
                    pos4=self._get_feature(features, 3, ""),
                    conj_type=self._get_feature(features, 4, ""),
                    conj_form=self._get_feature(features, 5, ""),
                    reading=self._get_feature(features, 6, ""),
                    pronunciation=self._get_feature(features, 9, ""),
                )
                tokens.append(token)
            node = node.next
        
        return tokens
    
    def _get_feature(self, features: List[str], index: int, default: str) -> str:
        """Safely get a feature by index, handling variable-length feature arrays."""
        if index < len(features) and features[index] != "*":
            return features[index]
        return default


# Module-level tokenizer instance for convenience
_default_tokenizer: Optional[Tokenizer] = None


def get_tokenizer() -> Tokenizer:
    """Get or create the default tokenizer instance."""
    global _default_tokenizer
    if _default_tokenizer is None:
        _default_tokenizer = Tokenizer()
    return _default_tokenizer


def tokenize(sentence: str) -> List[Token]:
    """Convenience function to tokenize using the default tokenizer."""
    return get_tokenizer().tokenize(sentence)


if __name__ == "__main__":
    # Demo/test
    test_sentences = [
        "私は猫が好きです。",
        "今日は天気がいいですね。",
        "彼女は本を読んでいます。",
    ]
    
    tokenizer = Tokenizer()
    for sentence in test_sentences:
        print(f"\n=== {sentence} ===")
        tokens = tokenizer.tokenize(sentence)
        for t in tokens:
            print(f"  {t.surface:8} | {t.pos1:6} | {t.lemma:8} | {t.reading}")

