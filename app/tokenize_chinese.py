"""
Jieba tokenization wrapper for Chinese text.
Similar to the Japanese MeCab + UniDic tokenizer, but for Mandarin Chinese.

Jieba is used because it:
- Properly preserves compound words (图书馆, 洗衣机, 程序员)
- Preserves person/place names (李明, 北京, 上海)
- Handles idioms consistently (keeps 4-char idioms together)
- Has highest agreement with other mainstream tokenizers (ltp, thulac, pkuseg)

Stanza was tested but over-splits compounds and names, making it unsuitable
for language learning where preserving meaningful units is important.
"""
from dataclasses import dataclass
from typing import List, Optional

try:
    import jieba
    import jieba.posseg as pseg
    jieba.setLogLevel(20)  # Suppress loading messages
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


@dataclass
class ChineseToken:
    """Represents a tokenized Chinese word with optional POS tag."""
    surface: str
    pos: str  # Part of speech tag


class ChineseTokenizer:
    """Jieba tokenizer for Chinese text."""

    def __init__(self, use_pos: bool = False):
        """
        Initialize the tokenizer.

        Args:
            use_pos: Whether to include POS tagging.
        """
        if not JIEBA_AVAILABLE:
            raise ImportError("jieba is not installed. Run: pip install jieba")

        self.use_pos = use_pos

    def tokenize(self, sentence: str) -> List[ChineseToken]:
        """
        Tokenize a Chinese sentence into words with POS tags.

        Args:
            sentence: Chinese text to tokenize

        Returns:
            List of ChineseToken objects with word and POS information
        """
        tokens = []

        if self.use_pos:
            for word, pos in pseg.cut(sentence):
                if word.strip():
                    tokens.append(ChineseToken(surface=word, pos=pos))
        else:
            for word in jieba.cut(sentence):
                if word.strip():
                    tokens.append(ChineseToken(surface=word, pos=""))

        return tokens

    def tokenize_simple(self, sentence: str) -> List[str]:
        """
        Tokenize a Chinese sentence into words (surface forms only).

        Args:
            sentence: Chinese text to tokenize

        Returns:
            List of word strings
        """
        return [word for word in jieba.cut(sentence) if word.strip()]


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
        "梦想成真。",  # Kept as unit (idiom)
        "我希望我的梦想成真。",
        "我在图书馆看书。",  # 图书馆 preserved
        "他是一个电脑程序员。",  # 程序员 preserved
    ]

    if JIEBA_AVAILABLE:
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
        print("jieba is not installed. Run: pip install jieba")
