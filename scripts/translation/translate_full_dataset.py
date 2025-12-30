#!/usr/bin/env python3
"""
Translate the full deduplicated Tatoeba dataset using Gemini 3 Flash.
Outputs to data/translated/ for further processing.
"""

import json
import os
import sys
import time
from pathlib import Path

try:
    from google import genai
except ImportError:
    print("Please install the Google AI SDK: pip install google-genai")
    sys.exit(1)

# Configuration
MODEL_NAME = "gemini-3-flash-preview"
BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY = 20  # seconds

SYSTEM_PROMPT = """What's the most natural spoken casual Japanese way to express the following? Output only the Japanese sentence in japanese not romaji.

Return ONLY a JSON array of translations in the same order as input.
Example input: ["Hello", "How are you?"]
Example output: ["やあ", "元気？"]"""


def load_deduplicated_sentences(data_dir: Path) -> list[dict]:
    """Load sentences from deduplicated Tatoeba files."""
    en_file = data_dir / "raw/tatoeba/Tatoeba.en-ja.dedup.en"
    ja_file = data_dir / "raw/tatoeba/Tatoeba.en-ja.dedup.ja"
    
    with open(en_file, "r", encoding="utf-8") as f:
        en_lines = [line.strip() for line in f.readlines()]
    with open(ja_file, "r", encoding="utf-8") as f:
        ja_lines = [line.strip() for line in f.readlines()]
    
    return [{"id": i, "en": en, "ja": ja} for i, (en, ja) in enumerate(zip(en_lines, ja_lines))]


def translate_batch(client, sentences: list[str]) -> list[str]:
    """Translate a batch of sentences with retry logic."""
    prompt = f"Translate these English sentences to natural spoken Japanese:\n{json.dumps(sentences, ensure_ascii=False)}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=genai.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
            )
            
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            
            return json.loads(text)
        
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < MAX_RETRIES - 1:
                    print(f"      ⏸️  Rate limited, waiting {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                    continue
            raise e
    
    raise Exception("Max retries exceeded")


def main():
    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ GEMINI_API_KEY not set!")
        sys.exit(1)
    
    # Setup paths
    data_dir = Path(__file__).parent.parent / "data"
    output_dir = data_dir / "translated"
    output_dir.mkdir(exist_ok=True)
    
    # Check for existing progress
    progress_file = output_dir / "progress.json"
    output_file = output_dir / "translations.jsonl"
    
    start_idx = 0
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress = json.load(f)
            start_idx = progress.get("last_completed", 0)
        print(f"📂 Resuming from index {start_idx}")
    
    # Load sentences
    print("📚 Loading deduplicated sentences...")
    sentences = load_deduplicated_sentences(data_dir)
    total = len(sentences)
    print(f"   Total: {total:,} sentences")
    
    # Initialize client
    client = genai.Client(api_key=api_key)
    
    print(f"\n🤖 Model: {MODEL_NAME}")
    print(f"📦 Batch size: {BATCH_SIZE}")
    print(f"📊 Batches: {(total + BATCH_SIZE - 1) // BATCH_SIZE:,}")
    print(f"💾 Output: {output_file}\n")
    
    # Open output file in append mode
    mode = "a" if start_idx > 0 else "w"
    
    with open(output_file, mode, encoding="utf-8") as f:
        for i in range(start_idx, total, BATCH_SIZE):
            batch = sentences[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"⏳ Batch {batch_num:,}/{total_batches:,} (sentences {i:,}-{min(i+BATCH_SIZE, total):,})...")
            
            try:
                english_texts = [s["en"] for s in batch]
                translations = translate_batch(client, english_texts)
                
                # Write results
                for sent, new_ja in zip(batch, translations):
                    result = {
                        "id": sent["id"],
                        "en": sent["en"],
                        "ja": new_ja  # New translation
                    }
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                
                print(f"   ✅ Done!")
                
                # Save progress
                with open(progress_file, "w") as pf:
                    json.dump({"last_completed": i + BATCH_SIZE}, pf)
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                print(f"   💾 Progress saved at index {i}")
                sys.exit(1)
            
            # Small delay between batches
            time.sleep(0.3)
    
    print(f"\n✨ Complete! Translated {total:,} sentences")
    print(f"📁 Output: {output_file}")


if __name__ == "__main__":
    main()

