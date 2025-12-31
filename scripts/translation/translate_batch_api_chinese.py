#!/usr/bin/env python3
"""
Translate sentences to Chinese using Gemini Batch API for 50% cost reduction.
Uses the same English sentences from Japanese translations.
"""

import json
import os
import sys
import time
from pathlib import Path

# Load .env file from project root
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Please install the Google AI SDK: pip install google-genai")
    sys.exit(1)

# Configuration
MODEL_NAME = "gemini-3-flash-preview"
REQUESTS_PER_BATCH = 1000
SENTENCES_PER_REQUEST = 50

SYSTEM_PROMPT = """What's the most natural spoken casual Mandarin Chinese way to express the following? Output only the Chinese sentence in simplified Chinese characters.

Return ONLY a JSON array of translations in the same order as input.
Example input: ["Hello", "How are you?"]
Example output: ["你好", "你好吗？"]"""


def load_english_sentences(data_dir: Path) -> list[dict]:
    """Load English sentences from Japanese translations file."""
    translations_file = data_dir / "translated/translations.jsonl"
    
    sentences = []
    with open(translations_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                sentences.append({"id": data["id"], "en": data["en"]})
    
    return sentences


def create_batch_request(sentences: list[dict], start_idx: int) -> dict:
    """Create a batch request for a group of sentences."""
    english_texts = [s["en"] for s in sentences]
    prompt = f"Translate these English sentences to natural spoken Mandarin Chinese:\n{json.dumps(english_texts, ensure_ascii=False)}"
    
    return {
        "key": f"batch-{start_idx}-{start_idx + len(sentences)}",
        "request": {
            "contents": [{"parts": [{"text": prompt}], "role": "user"}],
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]}
        }
    }


def create_batch_file(sentences: list[dict], output_path: Path) -> None:
    """Create JSONL file for batch API."""
    with open(output_path, "w", encoding="utf-8") as f:
        for i in range(0, len(sentences), SENTENCES_PER_REQUEST):
            batch = sentences[i:i + SENTENCES_PER_REQUEST]
            request = create_batch_request(batch, i)
            f.write(json.dumps(request, ensure_ascii=False) + "\n")
    print(f"   Created {output_path} with {(len(sentences) + SENTENCES_PER_REQUEST - 1) // SENTENCES_PER_REQUEST} requests")


def submit_batch_job(client, file_path: Path, display_name: str):
    """Upload file and submit batch job."""
    print(f"📤 Uploading {file_path}...")
    uploaded_file = client.files.upload(
        file=str(file_path),
        config=types.UploadFileConfig(display_name=display_name, mime_type='application/jsonl')
    )
    print(f"   Uploaded: {uploaded_file.name}")
    
    print(f"📋 Creating batch job...")
    batch_job = client.batches.create(
        model=f"models/{MODEL_NAME}",
        src=uploaded_file.name,
        config={'display_name': display_name}
    )
    print(f"   Created: {batch_job.name}")
    return batch_job


def wait_for_job(client, job_name: str, poll_interval: int = 60):
    """Poll until job completes."""
    print(f"\n⏳ Waiting for job {job_name}...")
    while True:
        job = client.batches.get(name=job_name)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        
        if state in ('JOB_STATE_SUCCEEDED', 'SUCCEEDED'):
            print(f"   ✅ Job completed successfully!")
            return job
        elif state in ('JOB_STATE_FAILED', 'FAILED'):
            print(f"   ❌ Job failed!")
            return job
        elif state in ('JOB_STATE_CANCELLED', 'CANCELLED'):
            print(f"   ⚠️ Job was cancelled!")
            return job
        elif state in ('JOB_STATE_EXPIRED', 'EXPIRED'):
            print(f"   ⚠️ Job expired!")
            return job
        
        print(f"   Status: {state} - checking again in {poll_interval}s...")
        time.sleep(poll_interval)


def check_job_status(client, job_name: str):
    """Check status of a batch job."""
    job = client.batches.get(name=job_name)
    state = job.state.name if hasattr(job.state, 'name') else str(job.state)
    print(f"   Job: {job_name}")
    print(f"   Status: {state}")

    if hasattr(job, 'display_name') and job.display_name:
        print(f"   Name: {job.display_name}")
    if hasattr(job, 'create_time') and job.create_time:
        print(f"   Created: {job.create_time}")
    if hasattr(job, 'update_time') and job.update_time:
        print(f"   Updated: {job.update_time}")

    if hasattr(job, 'stats') and job.stats:
        stats = job.stats
        if hasattr(stats, 'total_count'):
            print(f"   Total requests: {stats.total_count}")
        if hasattr(stats, 'success_count'):
            print(f"   Succeeded: {stats.success_count}")
        if hasattr(stats, 'failure_count'):
            print(f"   Failed: {stats.failure_count}")

    if hasattr(job, 'error') and job.error:
        print(f"   Error: {job.error}")

    return job, state


def download_batch_results(client, file_name: str) -> str:
    """Download batch results file content."""
    import urllib.request

    api_key = os.environ.get("GEMINI_API_KEY")
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    url = f"{base_url}/{file_name}:download?key={api_key}&alt=media"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        print(f"   First attempt failed: {e.code}")
        url2 = f"{base_url}/{file_name}?key={api_key}&alt=media"
        try:
            req = urllib.request.Request(url2)
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8')
        except Exception as e2:
            print(f"   Second attempt failed: {e2}")
            return None


def process_batch_results(client, job, sentences: list[dict], start_idx: int, output_file: Path):
    """Process completed batch job results and append to translations file."""
    print(f"\n📥 Processing results...")

    responses = []

    if hasattr(job, 'dest') and job.dest:
        if hasattr(job.dest, 'inlined_responses') and job.dest.inlined_responses:
            responses = list(job.dest.inlined_responses)
            print(f"   Found {len(responses)} inline responses")
        elif hasattr(job.dest, 'file_name') and job.dest.file_name:
            print(f"   Downloading results from: {job.dest.file_name}")
            try:
                content = download_batch_results(client, job.dest.file_name)
                if content:
                    for line in content.strip().split('\n'):
                        if line.strip():
                            responses.append(json.loads(line))
                    print(f"   Downloaded {len(responses)} responses")
                else:
                    print(f"   ❌ Could not download file content")
                    return False
            except Exception as e:
                print(f"   ❌ Error downloading results: {e}")
                return False
        else:
            print(f"   ❌ No results found in job destination")
            return False
    else:
        print(f"   ❌ No destination in job response")
        return False

    keyed_translations = {}
    errors = 0

    for resp in responses:
        key = None
        if hasattr(resp, 'key'):
            key = resp.key
        elif isinstance(resp, dict) and 'key' in resp:
            key = resp['key']

        if not key:
            errors += 1
            continue

        try:
            parts = key.split('-')
            offset = int(parts[1])
        except:
            errors += 1
            continue

        text = None
        if hasattr(resp, 'response') and resp.response:
            text = resp.response.text.strip() if hasattr(resp.response, 'text') else str(resp.response)
        elif isinstance(resp, dict) and 'response' in resp:
            resp_data = resp.get('response', {})
            if 'candidates' in resp_data:
                try:
                    candidate = resp_data['candidates'][0]
                    content = candidate.get('content', {})
                    parts = content.get('parts', [])
                    if parts:
                        text = parts[0].get('text', '').strip()
                    # Fallback: try direct text field
                    if not text and 'text' in candidate:
                        text = candidate['text'].strip()
                except (KeyError, IndexError, TypeError) as e:
                    print(f"   ⚠️ Error extracting text from candidate: {e}")

        if not text:
            errors += 1
            continue

        try:
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            translations = json.loads(text)
            keyed_translations[offset] = translations
        except Exception as e:
            errors += 1
            print(f"   ⚠️ Error parsing response for key {key}: {e}")

    print(f"   Parsed {len(keyed_translations)} batches")

    results = []
    sorted_offsets = sorted(keyed_translations.keys())

    for offset in sorted_offsets:
        translations = keyed_translations[offset]
        batch_sentences = sentences[offset:offset + len(translations)]
        for sent, new_zh in zip(batch_sentences, translations):
            results.append({
                "id": sent["id"],
                "en": sent["en"],
                "zh": new_zh
            })

    with open(output_file, "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"   ✅ Processed {len(results)} translations")
    if errors > 0:
        print(f"   ⚠️ {errors} errors encountered")
    return len(results)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch API translation to Chinese")
    parser.add_argument("--status", action="store_true", help="Check status of pending job")
    parser.add_argument("--wait", action="store_true", help="Wait for job completion")
    parser.add_argument("--job", type=str, help="Specific job name to check")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ GEMINI_API_KEY not set!")
        sys.exit(1)

    data_dir = Path(__file__).parent.parent.parent / "data"
    output_dir = data_dir / "translated_chinese"
    batch_dir = output_dir / "batch_jobs"
    output_dir.mkdir(exist_ok=True)
    batch_dir.mkdir(exist_ok=True)

    progress_file = output_dir / "progress.json"
    output_file = output_dir / "translations.jsonl"

    client = genai.Client(api_key=api_key)
    job_files = list(batch_dir.glob("job_*.json"))

    if args.status or args.wait:
        if args.job:
            job_name = args.job
        elif job_files:
            with open(job_files[-1], "r") as f:
                job_info = json.load(f)
                job_name = job_info["job_name"]
        else:
            print("❌ No pending job found. Run without --status to create one.")
            sys.exit(1)

        job, state = check_job_status(client, job_name)

        if args.wait and state not in ('JOB_STATE_SUCCEEDED', 'SUCCEEDED', 'JOB_STATE_FAILED', 'FAILED'):
            job = wait_for_job(client, job_name)
            state = job.state.name if hasattr(job.state, 'name') else str(job.state)

        if state in ('JOB_STATE_SUCCEEDED', 'SUCCEEDED'):
            all_sentences = load_english_sentences(data_dir)
            with open(job_files[-1], "r") as f:
                job_info = json.load(f)
            start_idx = job_info["start_idx"]
            remaining = all_sentences[start_idx:]

            count = process_batch_results(client, job, remaining, start_idx, output_file)
            if count:
                with open(progress_file, "w") as f:
                    json.dump({"last_completed": start_idx + count}, f)
                print(f"\n✨ Done! Progress updated to {start_idx + count}")
        return

    start_idx = 0
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress = json.load(f)
            start_idx = progress.get("last_completed", 0)

    print("📚 Loading English sentences from Japanese translations...")
    all_sentences = load_english_sentences(data_dir)
    total = len(all_sentences)

    remaining = all_sentences[start_idx:]
    print(f"   Total: {total:,} sentences")
    print(f"   Already done: {start_idx:,} sentences")
    print(f"   Remaining: {len(remaining):,} sentences")

    if not remaining:
        print("\n✨ All sentences already translated!")
        return

    batch_file = batch_dir / f"batch_requests_{start_idx}.jsonl"
    print(f"\n📝 Creating batch request file...")
    create_batch_file(remaining, batch_file)

    job = submit_batch_job(client, batch_file, f"duozh-translation-{start_idx}")

    job_info_file = batch_dir / f"job_{start_idx}.json"
    with open(job_info_file, "w") as f:
        json.dump({"job_name": job.name, "start_idx": start_idx, "count": len(remaining)}, f)

    print(f"\n📊 Batch job submitted!")
    print(f"   Job name: {job.name}")
    print(f"   Sentences: {len(remaining):,}")
    print(f"   Expected: within 24 hours (usually faster)")
    print(f"\n💡 Run with --status to check, --wait to wait for completion")


if __name__ == "__main__":
    main()

