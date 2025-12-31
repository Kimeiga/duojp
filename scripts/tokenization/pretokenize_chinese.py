#!/usr/bin/env python3
"""
Pre-tokenize Chinese corpus sentences and output JSON chunks for serverless deployment.

This script:
1. Reads Chinese translations JSONL file (id, en, zh)
2. Tokenizes each Chinese sentence with LTP
3. Outputs JSON chunks (1000 sentences each)
4. Creates manifest.json with metadata
5. Creates distractors.json with common tokens for exercise generation

LTP (Language Technology Platform) is used because it:
- Splits measure words properly (三 + 个, 一 + 台) - essential for learners
- Splits verb + object (看 + 书) - learners see verbs separately
- Splits adverb + adjective (很 + 漂亮) - learners see 很 means "very"
- Preserves compound nouns (图书馆, 洗衣机, 热水澡)
- Preserves names (北京, 上海, 李明)

Usage:
    python scripts/tokenization/pretokenize_chinese.py --input data/translated_chinese/translations.jsonl --output data/static_chinese
"""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from ltp import LTP
except ImportError:
    print("Please install ltp: pip install ltp")
    sys.exit(1)

# Punctuation to filter out from tokens (Chinese + general)
PUNCTUATION = {
    # Chinese punctuation
    "。", "，", "、", "；", "：", "？", "！", "…", "—", "·",
    "「", "」", "『", "』", "（", "）", "【", "】", "《", "》",
    """, """, "'", "'", "〈", "〉",
    # General punctuation
    ".", ",", ";", ":", "?", "!", "(", ")", "[", "]",
    '"', "'", "-", "–", "—", " ", "　", "\t", "\n"
}

CHUNK_SIZE = 1000  # Sentences per chunk
NUM_DISTRACTORS = 500  # Top N tokens for distractor pool

# Common proper nouns (Chinese transliterated names) that should be kept as separate tokens
# LTP sometimes merges these with adjacent text
PROPER_NOUNS = {
    # Most common names in the dataset
    '汤姆', '玛丽', '杰克', '约翰', '本', '肯', '比尔', '鲍勃', '乔', '凯特',
    '迈克', '南希', '乔治', '麦克', '丹', '克里斯', '爱丽丝', '苏珊', '贝蒂',
    '保罗', '彼得', '海伦', '约翰逊', '布莱恩', '弗雷德', '丽莎', '罗伯特',
    '尼克', '亚当', '安迪', '丹尼尔', '马修', '马克', '史蒂夫', '凯文', '杰森',
    '杰夫', '威廉', '詹姆斯', '查尔斯', '亨利', '弗兰克', '艾伦', '安东尼',
    '大卫', '理查德', '托马斯', '迈克尔', '史蒂芬', '马丁', '拉里', '杰瑞',
    '山姆', '雷', '罗恩', '维克多', '沃尔特', '威尔', '格雷格', '里奥',
    # Female names
    '安娜', '艾米', '卡罗尔', '黛安', '伊丽莎白', '艾玛', '格蕾丝', '艾琳',
    '珍妮', '朱莉', '劳拉', '玛格丽特', '帕特里夏', '蕾切尔', '萨拉', '温迪',
    '芭芭拉', '辛西娅', '黛博拉', '伊芙', '琳达', '珍妮特', '简', '莎莉',
    '凯伦', '莫妮卡', '露西', '莉莉', '艾米丽', '格温', '凯莉', '吉尔',
    # Last names
    '史密斯', '威廉姆斯', '布朗', '琼斯', '米勒', '戴维斯', '加西亚', '威尔逊',
    '泰勒', '杰克逊', '怀特', '哈里斯', '克拉克', '刘易斯', '沃克', '霍尔',
    '斯科特', '格林', '亚当斯', '贝克', '尼尔森', '卡特', '米切尔', '罗伯茨',
    '特纳', '菲利普斯', '坎贝尔', '帕克', '埃文斯', '爱德华兹', '柯林斯',
}


def is_punctuation(text: str) -> bool:
    """Check if text is purely punctuation."""
    return all(c in PUNCTUATION for c in text)


def split_proper_nouns(tokens: List[str]) -> List[str]:
    """
    Post-process tokens to split any that contain known proper nouns.

    LTP sometimes merges proper nouns with adjacent text, e.g.:
    - "汤姆比杰克" should be ["汤姆", "比", "杰克"]
    - "汤姆牙" should be ["汤姆", "牙"]
    - "别理汤姆" should be ["别理", "汤姆"]

    BUT we skip tokens with middle dot (·) as these are full names like 汤姆·杰克逊
    """
    result = []
    for token in tokens:
        # Skip tokens with middle dot - these are intentional full names
        if '·' in token:
            result.append(token)
            continue

        # Check if any proper noun is contained in this token (but isn't the whole token)
        found_split = False
        for name in PROPER_NOUNS:
            if name in token and token != name:
                # Split around the name
                idx = token.find(name)
                before = token[:idx]
                after = token[idx + len(name):]

                # Recursively process parts (there might be multiple names)
                parts = []
                if before:
                    parts.extend(split_proper_nouns([before]))
                parts.append(name)
                if after:
                    parts.extend(split_proper_nouns([after]))

                result.extend(parts)
                found_split = True
                break

        if not found_split:
            result.append(token)

    return result


# Global LTP instance (lazy loaded)
_ltp = None

def get_ltp() -> LTP:
    """Get or initialize the LTP tokenizer."""
    global _ltp
    if _ltp is None:
        _ltp = LTP('LTP/small')
    return _ltp


def tokenize_sentence(zh_text: str) -> List[str]:
    """Tokenize Chinese text and return list of surface forms (no punctuation)."""
    ltp = get_ltp()
    output = ltp.pipeline([zh_text], tasks=['cws'])
    tokens = output.cws[0]
    # Filter punctuation
    tokens = [w for w in tokens if w.strip() and not is_punctuation(w)]
    # Post-process to split proper nouns that got merged
    tokens = split_proper_nouns(tokens)
    return tokens


def process_corpus(input_path: Path, output_dir: Path, verbose: bool = False):
    """Process corpus and output JSON chunks."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    
    token_counter: Counter = Counter()
    
    sentences: List[Dict[str, Any]] = []
    chunk_index = 0
    total_count = 0
    
    if verbose:
        print(f"Reading {input_path}...")
    
    with open(input_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            en_text = data.get("en", "")
            zh_text = data.get("zh", "")
            sent_id = data.get("id", total_count)
            
            if not zh_text:
                continue
            
            # Tokenize Chinese
            tokens = tokenize_sentence(zh_text)
            
            if not tokens:
                continue  # Skip empty tokenizations
            
            # Count tokens for distractor pool
            for t in tokens:
                token_counter[t] += 1
            
            sentences.append({
                "id": sent_id,
                "en": en_text,
                "zh": zh_text,
                "tokens": tokens
            })
            total_count += 1
            
            # Write chunk when full
            if len(sentences) >= CHUNK_SIZE:
                chunk_path = chunks_dir / f"{chunk_index}.json"
                with open(chunk_path, "w", encoding="utf-8") as cf:
                    json.dump(sentences, cf, ensure_ascii=False)
                if verbose:
                    print(f"  Wrote chunk {chunk_index} ({len(sentences)} sentences)")
                sentences = []
                chunk_index += 1
    
    # Write final partial chunk
    if sentences:
        chunk_path = chunks_dir / f"{chunk_index}.json"
        with open(chunk_path, "w", encoding="utf-8") as cf:
            json.dump(sentences, cf, ensure_ascii=False)
        if verbose:
            print(f"  Wrote chunk {chunk_index} ({len(sentences)} sentences)")
        chunk_index += 1
    
    # Write manifest
    manifest = {
        "total": total_count,
        "chunks": chunk_index,
        "chunk_size": CHUNK_SIZE,
        "source": input_path.name,
        "language": "zh"
    }
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)
    if verbose:
        print(f"Wrote manifest: {total_count} sentences in {chunk_index} chunks")
    
    # Write distractors (top N most common tokens)
    top_tokens = [token for token, _ in token_counter.most_common(NUM_DISTRACTORS)]
    distractors_path = output_dir / "distractors.json"
    with open(distractors_path, "w", encoding="utf-8") as df:
        json.dump(top_tokens, df, ensure_ascii=False)
    if verbose:
        print(f"Wrote {len(top_tokens)} distractors")
    
    return total_count, chunk_index


def main():
    parser = argparse.ArgumentParser(description="Pre-tokenize Chinese corpus")
    parser.add_argument("--input", "-i", required=True, help="Input JSONL file")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    total, chunks = process_corpus(input_path, output_dir, args.verbose)
    print(f"Done! Processed {total:,} sentences into {chunks} chunks")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()

