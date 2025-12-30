#!/usr/bin/env python3
"""Analyze tokenizer comparison results."""
import json

with open('/tmp/tokenizer_comparison.json', 'r') as f:
    data = json.load(f)

results = data['results']
tokenizer_names = ['jieba', 'stanza', 'thulac', 'ltp', 'pkuseg']

# Count agreements
identical = 0
different = []

for r in results:
    toks = list(r['tokenizations'].values())
    if all(t == toks[0] for t in toks):
        identical += 1
    else:
        different.append(r)

print("=" * 80)
print("AGREEMENT ANALYSIS")
print("=" * 80)
print(f"Total: {len(results)} | All agree: {identical} ({identical*100//len(results)}%) | Disagree: {len(different)}")

print("\n" + "=" * 80)
print("SENTENCES WHERE TOKENIZERS DISAGREE")
print("=" * 80)

for r in different:
    print(f"\n{r['sentence']} ({r['description']})")
    for name in tokenizer_names:
        print(f"  {name:8}: {r['tokenizations'][name]}")

# Pairwise agreement
print("\n" + "=" * 80)
print("PAIRWISE AGREEMENT %")
print("=" * 80)

matrix = {}
for n1 in tokenizer_names:
    matrix[n1] = {}
    for n2 in tokenizer_names:
        count = sum(1 for r in results if r['tokenizations'][n1] == r['tokenizations'][n2])
        matrix[n1][n2] = count * 100 // len(results)

print(f"\n{'':10}", end='')
for n in tokenizer_names:
    print(f"{n:8}", end='')
print()

for n1 in tokenizer_names:
    print(f"{n1:10}", end='')
    for n2 in tokenizer_names:
        print(f"{matrix[n1][n2]:7}%", end='')
    print()

# Average agreement
print("\n" + "=" * 80)
print("AVERAGE AGREEMENT WITH OTHERS")
print("=" * 80)
for n1 in tokenizer_names:
    avg = sum(matrix[n1][n2] for n2 in tokenizer_names if n2 != n1) / 4
    print(f"  {n1:10}: {avg:.1f}%")

