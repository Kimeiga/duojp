import json
import os

# Find sentences containing 汤姆 (Tom) and check their tokenization
data_dir = "frontend/static/data-zh/chunks"
tom_examples = []

for filename in sorted(os.listdir(data_dir)):
    if not filename.endswith('.json'):
        continue
    with open(os.path.join(data_dir, filename), 'r') as f:
        chunk = json.load(f)
        for sent in chunk:
            if '汤姆' in sent['zh']:
                tom_examples.append({
                    'zh': sent['zh'],
                    'en': sent['en'],
                    'tokens': sent['tokens']
                })

print(f"Found {len(tom_examples)} sentences with 汤姆 (Tom)\n")

# Show examples where 汤姆 might be combined with other characters
print("=== Examples where 汤姆 might not be its own token ===\n")
problematic = []
for ex in tom_examples:
    # Check if any token contains 汤姆 but is longer
    merged = [t for t in ex['tokens'] if '汤姆' in t and t != '汤姆']
    if merged:
        problematic.append(ex)
        print(f"Sentence: {ex['zh']}")
        print(f"English: {ex['en']}")
        print(f"Tokens: {ex['tokens']}")
        print(f"Merged tokens: {merged}")
        print()

print(f"\nTotal problematic: {len(problematic)} / {len(tom_examples)}")

# Show a few good examples too
print("\n=== Good examples (汤姆 as standalone token) ===\n")
good = [ex for ex in tom_examples if '汤姆' in ex['tokens']][:3]
for ex in good:
    print(f"Sentence: {ex['zh']}")
    print(f"Tokens: {ex['tokens']}")
    print()

