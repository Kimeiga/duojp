#!/usr/bin/env python3
"""
Translate sentences to Chinese using Gemini API in real-time.
Uses parallel requests for faster processing.
"""

import json
import os
import sys
import time
import argparse
import concurrent.futures
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Please install: pip install google-genai python-dotenv")
    sys.exit(1)

MODEL_NAME = "gemini-2.0-flash"
BATCH_SIZE = 25  # Sentences per API call
MAX_WORKERS = 5  # Parallel requests
RATE_LIMIT_DELAY = 0.5  # Seconds between batches

SYSTEM_PROMPT = """Translate English to natural spoken Mandarin Chinese (simplified).
Return ONLY a JSON array of translations in the same order as input.
Example: ["Hello", "How are you?"] → ["你好", "你好吗？"]"""

write_lock = Lock()
progress_lock = Lock()
completed_count = 0


def translate_batch(client, sentences: list[dict], batch_idx: int) -> list[dict]:
    """Translate a batch of sentences."""
    global completed_count
    
    english_texts = [s["en"] for s in sentences]
    prompt = f"Translate to Chinese:\n{json.dumps(english_texts, ensure_ascii=False)}"
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
            )
        )
        
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        translations = json.loads(text)
        
        results = []
        for i, s in enumerate(sentences):
            if i < len(translations):
                results.append({
                    "id": s["id"],
                    "en": s["en"],
                    "zh": translations[i]
                })
        
        with progress_lock:
            completed_count += len(results)
        
        return results
        
    except Exception as e:
        print(f"   ⚠️ Batch {batch_idx} failed: {e}")
        return []


def main():
    global completed_count
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit sentences to translate")
    parser.add_argument("--resume", action="store_true", help="Resume from last position")
    args = parser.parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Set GEMINI_API_KEY in .env file")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    data_dir = Path(__file__).parent.parent / "data"
    input_file = data_dir / "translated/translations.jsonl"
    output_dir = data_dir / "translated_chinese"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "translations.jsonl"
    progress_file = output_dir / "progress.json"
    
    # Load existing translations
    existing_ids = set()
    if args.resume and output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    existing_ids.add(json.loads(line)["id"])
    
    # Load English sentences
    print("📚 Loading English sentences...")
    sentences = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data["id"] not in existing_ids:
                    sentences.append({"id": data["id"], "en": data["en"]})
    
    if args.limit:
        sentences = sentences[:args.limit]
    
    print(f"   Total to translate: {len(sentences):,}")
    
    if not sentences:
        print("✨ All sentences already translated!")
        return
    
    # Split into batches
    batches = [sentences[i:i+BATCH_SIZE] for i in range(0, len(sentences), BATCH_SIZE)]
    print(f"   Batches: {len(batches)}")
    
    start_time = time.time()
    results = []
    
    print("\n🚀 Translating...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for i, batch in enumerate(batches):
            future = executor.submit(translate_batch, client, batch, i)
            futures[future] = i
            time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
        
        for future in concurrent.futures.as_completed(futures):
            batch_results = future.result()
            results.extend(batch_results)
            
            # Progress update
            elapsed = time.time() - start_time
            rate = completed_count / elapsed if elapsed > 0 else 0
            eta = (len(sentences) - completed_count) / rate if rate > 0 else 0
            print(f"   Progress: {completed_count:,}/{len(sentences):,} ({rate:.1f}/s, ETA: {eta/60:.1f}m)")
    
    # Write results
    print(f"\n💾 Writing {len(results):,} translations...")
    mode = "a" if args.resume else "w"
    with open(output_file, mode, encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    
    with open(progress_file, "w") as f:
        json.dump({"completed": len(existing_ids) + len(results)}, f)
    
    elapsed = time.time() - start_time
    print(f"\n✨ Done! Translated {len(results):,} sentences in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()

