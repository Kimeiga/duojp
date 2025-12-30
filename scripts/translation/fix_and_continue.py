#!/usr/bin/env python3
"""Fix romaji translations and continue from where we left off."""

import json
import os
import sys
import time
from pathlib import Path

try:
    from google import genai
except ImportError:
    print("Please install: pip install google-genai")
    sys.exit(1)

MODEL_NAME = "gemini-3-flash-preview"
BATCH_SIZE = 100

SYSTEM_PROMPT = """Task: Translate English -> Natural Spoken Japanese (Plain Form).

Constraints:
- Tone: Casual/Intimate (Friend-to-friend)
- Forbidden: Desu, Masu, literary "De aru", strong gendered endings
- Required: Spoken vocabulary, natural endings (yo, ne, n da), zero pronouns if context clear
- IMPORTANT: Write in Japanese script (hiragana, katakana, kanji). NEVER use romaji/English letters.

Output: Return ONLY a JSON array of translations in the same order as input.
Example: ["Hello"] -> ["やあ"]"""


def load_english_sentences(data_dir: Path) -> list[str]:
    """Load deduplicated English sentences."""
    with open(data_dir / "raw/tatoeba/Tatoeba.en-ja.dedup.en", "r") as f:
        return [line.strip() for line in f.readlines()]


def translate_batch(client, sentences: list[str]) -> list[str]:
    """Translate with retry logic."""
    prompt = f"Translate to Japanese:\n{json.dumps(sentences, ensure_ascii=False)}"
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME, contents=prompt,
                config=genai.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                print(f"      Rate limited, waiting 20s...")
                time.sleep(20)
                continue
            raise
    raise Exception("Max retries")


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY"); sys.exit(1)
    
    data_dir = Path(__file__).parent.parent / "data"
    output_file = data_dir / "translated/translations.jsonl"
    
    # Load existing translations
    existing = {}
    with open(output_file, "r") as f:
        for line in f:
            item = json.loads(line)
            existing[item["id"]] = item
    
    # Load all English sentences
    all_english = load_english_sentences(data_dir)
    total_sentences = len(all_english)
    
    # IDs to fix (romaji batch) and IDs to continue from
    romaji_ids = set(range(36600, 36700))
    last_id = max(existing.keys())
    
    print(f"📚 Total sentences: {total_sentences:,}")
    print(f"✅ Already done: {len(existing):,}")
    print(f"🔧 Romaji to fix: {len(romaji_ids)}")
    print(f"📝 Remaining: {total_sentences - last_id - 1:,}")
    
    client = genai.Client(api_key=api_key)
    
    # Step 1: Fix romaji translations
    print(f"\n🔧 Fixing romaji translations (IDs 36600-36699)...")
    fix_sentences = [all_english[i] for i in range(36600, 36700)]
    
    try:
        fixed = translate_batch(client, fix_sentences)
        for i, ja in enumerate(fixed):
            existing[36600 + i]["ja"] = ja
        print(f"   ✅ Fixed 100 sentences")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)
    
    # Rewrite file with fixes
    print("💾 Saving fixed translations...")
    with open(output_file, "w") as f:
        for i in sorted(existing.keys()):
            f.write(json.dumps(existing[i], ensure_ascii=False) + "\n")
    
    # Step 2: Continue from where we left off
    start_id = last_id + 1
    print(f"\n📝 Continuing from ID {start_id}...")
    
    with open(output_file, "a") as f:
        for i in range(start_id, total_sentences, BATCH_SIZE):
            batch_ids = list(range(i, min(i + BATCH_SIZE, total_sentences)))
            batch_en = [all_english[j] for j in batch_ids]
            batch_num = (i - start_id) // BATCH_SIZE + 1
            total_batches = (total_sentences - start_id + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"⏳ Batch {batch_num:,}/{total_batches:,} (IDs {i}-{i+len(batch_ids)-1})...")
            
            try:
                translations = translate_batch(client, batch_en)
                for j, ja in zip(batch_ids, translations):
                    f.write(json.dumps({"id": j, "en": all_english[j], "ja": ja}, ensure_ascii=False) + "\n")
                print(f"   ✅ Done")
            except Exception as e:
                print(f"   ❌ Error at ID {i}: {e}")
                print(f"   💾 Progress saved. Re-run to continue.")
                sys.exit(1)
            
            time.sleep(0.3)
    
    print(f"\n✨ Complete! All {total_sentences:,} sentences translated.")


if __name__ == "__main__":
    main()

