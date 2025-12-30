#!/usr/bin/env python3
"""
Translate English sentences to natural spoken Japanese using Gemini 3 Flash.
Supports comparing different thinking levels.
"""

import argparse
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
MODEL_NAME = "gemini-3-flash-preview"  # Gemini 3 Flash
BATCH_SIZE = 1  # Sentences per API call (testing batch size 1)

SYSTEM_PROMPT = """Task: Translate English -> Natural Spoken Japanese (Plain Form).

Constraints:
- Tone: Casual/Intimate (Friend-to-friend)
- Forbidden: Desu, Masu, literary "De aru", strong gendered endings
- Required: Spoken vocabulary, natural endings (yo, ne, n da), zero pronouns if context clear

Output format: Return ONLY a JSON array of translations in the same order as input.
Example input: ["Hello", "How are you?"]
Example output: ["やあ", "元気？"]

Do NOT include any explanation, just the JSON array."""


def load_sentences(chunk_path: Path, limit: int = 100) -> list[dict]:
    """Load sentences from a chunk file."""
    with open(chunk_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data[:limit]


def translate_batch(client, sentences: list[str], thinking_level: str = None) -> list[str]:
    """Translate a batch of sentences."""
    prompt = f"Translate these English sentences to natural spoken Japanese:\n{json.dumps(sentences, ensure_ascii=False)}"

    # Build config with optional thinking level
    config_kwargs = {"system_instruction": SYSTEM_PROMPT}
    if thinking_level:
        config_kwargs["thinking_config"] = genai.types.ThinkingConfig(
            thinking_level=thinking_level
        )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=genai.types.GenerateContentConfig(**config_kwargs)
    )

    # Parse the JSON response
    text = response.text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


def main():
    parser = argparse.ArgumentParser(description="Translate English to Japanese using Gemini 3 Flash")
    parser.add_argument("--thinking", choices=["minimal", "low", "medium", "high"],
                        help="Thinking level (default: dynamic/high)")
    parser.add_argument("--compare", action="store_true",
                        help="Compare with previous results (translation_results.json)")
    parser.add_argument("--compare-batch", action="store_true",
                        help="Compare batch size effect (previous batch 10 vs current batch size)")
    parser.add_argument("--limit", type=int, default=100,
                        help="Number of sentences to translate (default: 100)")
    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ GEMINI_API_KEY not set!")
        print("\n📋 How to get your API key:")
        print("   1. Go to: https://aistudio.google.com/apikey")
        print("   2. Click 'Create API key'")
        print("   3. Copy the key (starts with 'AIza...')")
        print("   4. Run: export GEMINI_API_KEY='your-key-here'")
        print("   5. Then run this script again\n")
        sys.exit(1)

    # Initialize client
    client = genai.Client(api_key=api_key)

    # Load sentences
    chunk_path = Path(__file__).parent.parent / "frontend/static/data/chunks/0.json"
    sentences = load_sentences(chunk_path, limit=args.limit)

    # Load previous results if comparing
    previous_results = {}
    compare_mode = None
    if args.compare or args.compare_batch:
        prev_path = Path(__file__).parent / "translation_results.json"
        if prev_path.exists():
            with open(prev_path, "r", encoding="utf-8") as f:
                for r in json.load(f):
                    previous_results[r["id"]] = r["new_ja"]
            compare_mode = "batch" if args.compare_batch else "thinking"
            label = "batch size 10" if args.compare_batch else "previous"
            print(f"📊 Loaded {len(previous_results)} translations from {label} for comparison")
        else:
            print("⚠️  No previous results found. Run without --compare first.")
            sys.exit(1)

    thinking_label = args.thinking or "dynamic (high)"
    print(f"📚 Loaded {len(sentences)} sentences")
    print(f"🤖 Using model: {MODEL_NAME}")
    print(f"🧠 Thinking level: {thinking_label}")
    print(f"📦 Batch size: {BATCH_SIZE}\n")

    results = []

    # Process in batches
    for i in range(0, len(sentences), BATCH_SIZE):
        batch = sentences[i:i + BATCH_SIZE]
        english_texts = [s["en"] for s in batch]

        print(f"⏳ Translating batch {i // BATCH_SIZE + 1}/{(len(sentences) + BATCH_SIZE - 1) // BATCH_SIZE}...")

        try:
            translations = translate_batch(client, english_texts, args.thinking)

            for j, (sent, new_ja) in enumerate(zip(batch, translations)):
                result = {
                    "id": sent["id"],
                    "en": sent["en"],
                    "original_ja": sent["ja"],
                }
                if compare_mode == "batch" and sent["id"] in previous_results:
                    result["ja_batch10"] = previous_results[sent["id"]]
                    result["ja_batch100"] = new_ja
                elif compare_mode == "thinking" and sent["id"] in previous_results:
                    result["ja_high"] = previous_results[sent["id"]]
                    result["ja_minimal"] = new_ja
                else:
                    result["new_ja"] = new_ja
                results.append(result)

            print(f"   ✅ Done! ({len(translations)} translations)")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            # Add placeholders for failed batch
            for sent in batch:
                result = {
                    "id": sent["id"],
                    "en": sent["en"],
                    "original_ja": sent["ja"],
                }
                if compare_mode == "batch":
                    result["ja_batch10"] = previous_results.get(sent["id"], "[N/A]")
                    result["ja_batch100"] = f"[ERROR: {e}]"
                elif compare_mode == "thinking":
                    result["ja_high"] = previous_results.get(sent["id"], "[N/A]")
                    result["ja_minimal"] = f"[ERROR: {e}]"
                else:
                    result["new_ja"] = f"[ERROR: {e}]"
                results.append(result)

        # Small delay to avoid rate limits
        time.sleep(0.5)

    # Save results
    if args.compare_batch:
        output_file = "translation_batch_comparison.json"
    elif args.compare:
        output_file = "translation_comparison.json"
    else:
        output_file = "translation_results.json"

    output_path = Path(__file__).parent / output_file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✨ Done! Results saved to: {output_path}")
    print(f"📊 Total: {len(results)} sentences translated")

    # Print sample for review
    print("\n" + "="*60)
    if args.compare_batch:
        print("BATCH SIZE COMPARISON (first 5 differences):")
        print("="*60)
        diff_count = 0
        for r in results:
            if r.get("ja_batch10") != r.get("ja_batch100"):
                diff_count += 1
                print(f"\n🇬🇧 {r['en']}")
                print(f"📖 Original:     {r['original_ja']}")
                print(f"📦 Batch 10:     {r.get('ja_batch10', 'N/A')}")
                print(f"📦 Batch 100:    {r.get('ja_batch100', 'N/A')}")
                if diff_count >= 5:
                    break
        total_diff = sum(1 for r in results if r.get("ja_batch10") != r.get("ja_batch100"))
        print(f"\n📊 Total differences: {total_diff}/{len(results)} sentences")
    elif args.compare:
        print("THINKING LEVEL COMPARISON (first 5 differences):")
        print("="*60)
        diff_count = 0
        for r in results:
            if r.get("ja_high") != r.get("ja_minimal"):
                diff_count += 1
                print(f"\n🇬🇧 {r['en']}")
                print(f"📖 Original:    {r['original_ja']}")
                print(f"🧠 High:        {r.get('ja_high', 'N/A')}")
                print(f"⚡ Minimal:     {r.get('ja_minimal', 'N/A')}")
                if diff_count >= 5:
                    break
        total_diff = sum(1 for r in results if r.get("ja_high") != r.get("ja_minimal"))
        print(f"\n📊 Total differences: {total_diff}/{len(results)} sentences")
    else:
        print("SAMPLE TRANSLATIONS (first 5):")
        print("="*60)
        for r in results[:5]:
            print(f"\n🇬🇧 {r['en']}")
            print(f"📖 Original: {r['original_ja']}")
            print(f"✨ New:      {r['new_ja']}")


if __name__ == "__main__":
    main()

