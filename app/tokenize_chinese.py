"""
LTP tokenization wrapper for Chinese text.
Similar to the Japanese MeCab + UniDic tokenizer, but for Mandarin Chinese.

LTP (Language Technology Platform) is used because it:
- Splits measure words properly (三 + 个, 一 + 台) - essential for learners
- Splits verb + object (看 + 书) - learners see verbs separately
- Splits adverb + adjective (很 + 漂亮) - learners see 很 means "very"
- Preserves compound nouns (图书馆, 洗衣机, 热水澡)
- Preserves names (北京, 上海, 李明)

Tested alternatives:
- jieba: Over-groups (merges 一个舒服, 看书, 很漂亮) - bad for learning
- stanza: Over-splits compounds (图书馆→图书+馆) - bad for learning
"""
from dataclasses import dataclass
from typing import List, Optional

try:
    from ltp import LTP
    LTP_AVAILABLE = True
except ImportError:
    LTP_AVAILABLE = False


@dataclass
class ChineseToken:
    """Represents a tokenized Chinese word with optional POS tag."""
    surface: str
    pos: str  # Part of speech tag


# Global LTP instance (lazy loaded, as it's heavy)
_ltp_instance: Optional[LTP] = None


def _get_ltp() -> LTP:
    """Get or create the LTP instance."""
    global _ltp_instance
    if _ltp_instance is None:
        _ltp_instance = LTP('LTP/small')
    return _ltp_instance


class ChineseTokenizer:
    """LTP tokenizer for Chinese text."""

    def __init__(self, use_pos: bool = False):
        """
        Initialize the tokenizer.

        Args:
            use_pos: Whether to include POS tagging.
        """
        if not LTP_AVAILABLE:
            raise ImportError("ltp is not installed. Run: pip install ltp")

        self.use_pos = use_pos
        self.ltp = _get_ltp()

    def tokenize(self, sentence: str) -> List[ChineseToken]:
        """
        Tokenize a Chinese sentence into words with POS tags.

        Args:
            sentence: Chinese text to tokenize

        Returns:
            List of ChineseToken objects with word and POS information
        """
        tasks = ['cws', 'pos'] if self.use_pos else ['cws']
        output = self.ltp.pipeline([sentence], tasks=tasks)

        tokens = []
        words = output.cws[0]
        pos_tags = output.pos[0] if self.use_pos else [''] * len(words)

        for word, pos in zip(words, pos_tags):
            if word.strip():
                tokens.append(ChineseToken(surface=word, pos=pos))

        return tokens

    def tokenize_simple(self, sentence: str) -> List[str]:
        """
        Tokenize a Chinese sentence into words (surface forms only).

        Args:
            sentence: Chinese text to tokenize

        Returns:
            List of word strings
        """
        output = self.ltp.pipeline([sentence], tasks=['cws'])
        return [word for word in output.cws[0] if word.strip()]


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
        "她正在看一本书。",  # 看 + 书 split (verb + object)
        "你好，你叫什么名字？",
        "我希望我的梦想成真。",  # 梦想 + 成真 split
        "我在图书馆看书。",  # 图书馆 preserved, 看 + 书 split
        "他是一个电脑程序员。",  # 一 + 个 split (number + measure)
        "没有什么比得上一个舒服的热水澡了。",  # Key test case
    ]

    if LTP_AVAILABLE:
        tokenizer = ChineseTokenizer()
        for sentence in test_sentences:
            print(f"\n=== {sentence} ===")
            simple = tokenizer.tokenize_simple(sentence)
            print(f"  {simple}")
    else:
        print("ltp is not installed. Run: pip install ltp")
