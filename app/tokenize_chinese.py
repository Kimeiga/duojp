"""
Stanza tokenization wrapper for Chinese text.
Similar to the Japanese MeCab + UniDic tokenizer, but for Mandarin Chinese.

Stanza (Stanford NLP) is preferred over jieba because it properly splits
4-character idioms like "梦想成真" into "梦想" + "成真" which is better
for language learning exercises.
"""
from dataclasses import dataclass
from typing import List, Optional

try:
    import stanza
    STANZA_AVAILABLE = True
except ImportError:
    STANZA_AVAILABLE = False


@dataclass
class ChineseToken:
    """Represents a tokenized Chinese word with optional POS tag."""
    surface: str
    pos: str  # Part of speech tag (UPOS)


class ChineseTokenizer:
    """Stanza tokenizer for Chinese text."""

    def __init__(self, use_pos: bool = False):
        """
        Initialize the tokenizer.

        Args:
            use_pos: Whether to include POS tagging (slower but more info).
        """
        if not STANZA_AVAILABLE:
            raise ImportError("stanza is not installed. Run: pip install stanza")

        processors = 'tokenize,pos' if use_pos else 'tokenize'
        self.nlp = stanza.Pipeline('zh', processors=processors, verbose=False)
        self.use_pos = use_pos

    def tokenize(self, sentence: str) -> List[ChineseToken]:
        """
        Tokenize a Chinese sentence into words with POS tags.

        Args:
            sentence: Chinese text to tokenize

        Returns:
            List of ChineseToken objects with word and POS information
        """
        doc = self.nlp(sentence)
        tokens = []

        for sent in doc.sentences:
            for word in sent.words:
                if word.text.strip():
                    pos = word.upos if self.use_pos else ""
                    tokens.append(ChineseToken(surface=word.text, pos=pos))

        return tokens

    def tokenize_simple(self, sentence: str) -> List[str]:
        """
        Tokenize a Chinese sentence into words (surface forms only).

        Args:
            sentence: Chinese text to tokenize

        Returns:
            List of word strings
        """
        doc = self.nlp(sentence)
        return [token.text for sent in doc.sentences for token in sent.tokens if token.text.strip()]


# Module-level tokenizer instance for convenience
_default_tokenizer: Optional[ChineseTokenizer] = None


def get_tokenizer() -> ChineseTokenizer:
    """Get or create the default tokenizer instance."""
    global _default_tokenizer
    if _default_tokenizer is None:
        _default_tokenizer = ChineseTokenizer()
    return _default_tokenizer


def tokenize(sentence: str) -> List[ChineseToken]:
    """Convenience function to tokenize using the default tokenizer."""
    return get_tokenizer().tokenize(sentence)


def tokenize_simple(sentence: str) -> List[str]:
    """Convenience function to get just word surfaces."""
    return get_tokenizer().tokenize_simple(sentence)


if __name__ == "__main__":
    # Demo/test
    test_sentences = [
        "我爱北京天安门。",
        "今天天气真好！",
        "她正在看一本书。",
        "你好，你叫什么名字？",
        "梦想成真。",  # Should split into 梦想 + 成真
        "我希望我的梦想成真。",
    ]

    if STANZA_AVAILABLE:
        tokenizer = ChineseTokenizer()
        for sentence in test_sentences:
            print(f"\n=== {sentence} ===")
            tokens = tokenizer.tokenize(sentence)
            for t in tokens:
                print(f"  {t.surface:8}")

            # Also show simple tokenization
            simple = tokenizer.tokenize_simple(sentence)
            print(f"  Simple: {simple}")
    else:
        print("stanza is not installed. Run: pip install stanza")

