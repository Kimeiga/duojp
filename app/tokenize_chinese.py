"""
jieba tokenization wrapper for Chinese text.
Similar to the Japanese MeCab + UniDic tokenizer, but for Mandarin Chinese.
"""
from dataclasses import dataclass
from typing import List, Optional

try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


@dataclass
class ChineseToken:
    """Represents a tokenized Chinese word with optional POS tag."""
    surface: str
    pos: str  # Part of speech tag


class ChineseTokenizer:
    """jieba tokenizer for Chinese text."""
    
    def __init__(self, use_paddle: bool = False):
        """
        Initialize the tokenizer.
        
        Args:
            use_paddle: Whether to use PaddlePaddle for more accurate segmentation.
                        Requires paddlepaddle package to be installed.
        """
        if not JIEBA_AVAILABLE:
            raise ImportError("jieba is not installed. Run: pip install jieba")
        
        self.use_paddle = use_paddle
        if use_paddle:
            jieba.enable_paddle()
    
    def tokenize(self, sentence: str) -> List[ChineseToken]:
        """
        Tokenize a Chinese sentence into words with POS tags.
        
        Args:
            sentence: Chinese text to tokenize
            
        Returns:
            List of ChineseToken objects with word and POS information
        """
        tokens = []
        words = pseg.cut(sentence)
        
        for word, flag in words:
            if word.strip():  # Skip empty tokens
                tokens.append(ChineseToken(surface=word, pos=flag))
        
        return tokens
    
    def tokenize_simple(self, sentence: str) -> List[str]:
        """
        Tokenize a Chinese sentence into words (surface forms only).
        
        Args:
            sentence: Chinese text to tokenize
            
        Returns:
            List of word strings
        """
        return [word for word in jieba.lcut(sentence) if word.strip()]


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
    ]
    
    if JIEBA_AVAILABLE:
        tokenizer = ChineseTokenizer()
        for sentence in test_sentences:
            print(f"\n=== {sentence} ===")
            tokens = tokenizer.tokenize(sentence)
            for t in tokens:
                print(f"  {t.surface:8} | {t.pos}")
            
            # Also show simple tokenization
            simple = tokenizer.tokenize_simple(sentence)
            print(f"  Simple: {simple}")
    else:
        print("jieba is not installed. Run: pip install jieba")

