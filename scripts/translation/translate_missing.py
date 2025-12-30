#!/usr/bin/env python3
"""Translate missing sentences one at a time using Gemini."""
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google import genai
from google.genai import types

MODEL_NAME = "gemini-2.0-flash"

# Load existing translations
translated_ids = set()
with open('data/translated_chinese/translations.jsonl', 'r') as f:
    for line in f:
        data = json.loads(line)
        translated_ids.add(data['id'])

# Load English sentences from the translated file
english = []
with open('data/translated/translations.jsonl', 'r') as f:
    for line in f:
        data = json.loads(line)
        english.append({'id': data['id'], 'en': data['en']})

# Find missing
missing = [s for s in english if s['id'] not in translated_ids]
print(f'Missing: {len(missing)}')

if missing:
    client = genai.Client()

    for s in missing:
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=f"Translate to Chinese. Return ONLY the translation:\n{s['en']}",
                config=types.GenerateContentConfig(temperature=0.3)
            )
            zh = response.text.strip()
            with open('data/translated_chinese/translations.jsonl', 'a') as f:
                f.write(json.dumps({'id': s['id'], 'en': s['en'], 'zh': zh}, ensure_ascii=False) + '\n')
            print(f"{s['id']}: {s['en'][:50]} -> {zh[:50]}")
        except Exception as e:
            print(f"Error {s['id']}: {e}")

