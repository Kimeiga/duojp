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


def is_punctuation(text: str) -> bool:
    """Check if text is purely punctuation."""
    return all(c in PUNCTUATION for c in text)


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
    return [w for w in tokens if w.strip() and not is_punctuation(w)]


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

