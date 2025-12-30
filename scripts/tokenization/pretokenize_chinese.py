#!/usr/bin/env python3
"""
Pre-tokenize Chinese corpus sentences and output JSON chunks for serverless deployment.

This script:
1. Reads Chinese translations JSONL file (id, en, zh)
2. Tokenizes each Chinese sentence with jieba
3. Outputs JSON chunks (1000 sentences each)
4. Creates manifest.json with metadata
5. Creates distractors.json with common tokens for exercise generation

Jieba is used because it:
- Properly preserves compound words (图书馆, 洗衣机, 程序员)
- Preserves person/place names (李明, 北京, 上海)
- Handles idioms consistently (keeps 4-char idioms together)
- Has highest agreement with other mainstream tokenizers (ltp, thulac, pkuseg)

Usage:
    python scripts/pretokenize_chinese.py --input data/translated_chinese/translations.jsonl --output data/static_chinese
"""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import jieba
    jieba.setLogLevel(20)  # Suppress loading messages
except ImportError:
    print("Please install jieba: pip install jieba")
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


def tokenize_sentence(zh_text: str) -> List[str]:
    """Tokenize Chinese text and return list of surface forms (no punctuation)."""
    tokens = list(jieba.cut(zh_text))
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

