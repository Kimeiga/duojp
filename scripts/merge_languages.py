#!/usr/bin/env python3
"""
Merge tokenized data from all languages into a unified format.

This script:
1. Reads from data-ja, data-zh, data-ko directories
2. Matches sentences by their shared English text
3. Creates unified chunks with all translations
4. Outputs to data-unified directory

Unified format:
{
  "id": 0,
  "en": "Let's try something.",
  "translations": {
    "ja": { "text": "何かしてみましょう。", "tokens": ["何", "か", ...] },
    "zh": { "text": "咱们试试看。", "tokens": ["咱们", "试试", "看"] },
    "ko": { "text": "뭔가 해보자.", "tokens": ["뭔가", "해", "보", "자"] }
  }
}

Usage:
    python scripts/merge_languages.py --output frontend/static/data-unified
"""
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

CHUNK_SIZE = 1000
LANGUAGES = ['ja', 'zh', 'ko', 'tr']


def load_language_data(data_dir: Path, lang: str) -> Dict[str, Dict]:
    """Load all sentences from a language's chunk files, indexed by English text."""
    chunks_dir = data_dir / "chunks"
    if not chunks_dir.exists():
        print(f"  Warning: {chunks_dir} not found")
        return {}
    
    sentences = {}
    chunk_files = sorted(chunks_dir.glob("*.json"))
    
    for chunk_file in chunk_files:
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunk = json.load(f)
            for sent in chunk:
                en = sent.get("en", "").strip()
                if en:
                    sentences[en] = {
                        "text": sent.get(lang, ""),
                        "tokens": sent.get("tokens", [])
                    }
    
    return sentences


def merge_languages(static_dir: Path, output_dir: Path, verbose: bool = False):
    """Merge all language data into unified format."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    
    # Load Japanese as base (has the sentence IDs)
    print("Loading Japanese data (base)...")
    ja_dir = static_dir / "data"
    ja_chunks_dir = ja_dir / "chunks"
    
    if not ja_chunks_dir.exists():
        print(f"Error: Japanese data not found at {ja_chunks_dir}")
        return
    
    # Load other languages indexed by English text
    print("Loading Chinese data...")
    zh_data = load_language_data(static_dir / "data-zh", "zh")
    print(f"  Loaded {len(zh_data)} Chinese sentences")

    print("Loading Korean data...")
    ko_data = load_language_data(static_dir / "data-ko", "ko")
    print(f"  Loaded {len(ko_data)} Korean sentences")

    print("Loading Turkish data...")
    tr_data = load_language_data(static_dir / "data-tr", "tr")
    print(f"  Loaded {len(tr_data)} Turkish sentences")
    
    # Process Japanese chunks and merge
    print("Merging languages...")
    unified_sentences: List[Dict[str, Any]] = []
    chunk_index = 0
    total_count = 0
    matched_zh = 0
    matched_ko = 0
    matched_tr = 0

    ja_chunk_files = sorted(ja_chunks_dir.glob("*.json"))
    
    for chunk_file in ja_chunk_files:
        with open(chunk_file, "r", encoding="utf-8") as f:
            ja_chunk = json.load(f)
        
        for sent in ja_chunk:
            en = sent.get("en", "").strip()
            
            unified = {
                "id": sent.get("id", total_count),
                "en": en,
                "translations": {
                    "ja": {
                        "text": sent.get("ja", ""),
                        "tokens": sent.get("tokens", [])
                    }
                }
            }
            
            # Add Chinese if available
            if en in zh_data:
                unified["translations"]["zh"] = zh_data[en]
                matched_zh += 1
            
            # Add Korean if available
            if en in ko_data:
                unified["translations"]["ko"] = ko_data[en]
                matched_ko += 1

            # Add Turkish if available
            if en in tr_data:
                unified["translations"]["tr"] = tr_data[en]
                matched_tr += 1

            unified_sentences.append(unified)
            total_count += 1
            
            # Write chunk when full
            if len(unified_sentences) >= CHUNK_SIZE:
                chunk_path = chunks_dir / f"{chunk_index}.json"
                with open(chunk_path, "w", encoding="utf-8") as cf:
                    json.dump(unified_sentences, cf, ensure_ascii=False)
                if verbose:
                    print(f"  Wrote chunk {chunk_index} ({len(unified_sentences)} sentences)")
                unified_sentences = []
                chunk_index += 1
    
    # Write final partial chunk
    if unified_sentences:
        chunk_path = chunks_dir / f"{chunk_index}.json"
        with open(chunk_path, "w", encoding="utf-8") as cf:
            json.dump(unified_sentences, cf, ensure_ascii=False)
        if verbose:
            print(f"  Wrote chunk {chunk_index} ({len(unified_sentences)} sentences)")
        chunk_index += 1
    
    # Write manifest
    manifest = {
        "total": total_count,
        "chunks": chunk_index,
        "chunk_size": CHUNK_SIZE,
        "languages": ["ja", "zh", "ko", "tr"],
        "matched_zh": matched_zh,
        "matched_ko": matched_ko,
        "matched_tr": matched_tr
    }
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    # Merge distractors from all languages
    all_distractors = {"ja": [], "zh": [], "ko": [], "tr": []}

    for lang, subdir in [("ja", "data"), ("zh", "data-zh"), ("ko", "data-ko"), ("tr", "data-tr")]:
        distractor_file = static_dir / subdir / "distractors.json"
        if distractor_file.exists():
            with open(distractor_file, "r", encoding="utf-8") as df:
                all_distractors[lang] = json.load(df)

    distractors_path = output_dir / "distractors.json"
    with open(distractors_path, "w", encoding="utf-8") as df:
        json.dump(all_distractors, df, ensure_ascii=False)

    print(f"\n✅ Merge complete!")
    print(f"   Total sentences: {total_count:,}")
    print(f"   Chinese matches: {matched_zh:,} ({100*matched_zh/total_count:.1f}%)")
    print(f"   Korean matches: {matched_ko:,} ({100*matched_ko/total_count:.1f}%)")
    print(f"   Turkish matches: {matched_tr:,} ({100*matched_tr/total_count:.1f}%)")
    print(f"   Chunks written: {chunk_index}")
    print(f"   Output: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Merge language data")
    parser.add_argument("--static", default="frontend/static", help="Static directory with data-* folders")
    parser.add_argument("--output", "-o", default="frontend/static/data-unified", help="Output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    static_dir = Path(args.static)
    output_dir = Path(args.output)

    merge_languages(static_dir, output_dir, args.verbose)


if __name__ == "__main__":
    main()

