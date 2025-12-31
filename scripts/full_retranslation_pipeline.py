#!/usr/bin/env python3
"""
Full pipeline to retranslate Chinese and Korean with Gemini 3 Flash,
then tokenize, merge, and prepare for deployment.
"""

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

def run_command(cmd, cwd=None, check=True):
    """Run a command and stream output."""
    print(f"\n{'='*60}")
    print(f"Running: {cmd}")
    print('='*60)
    result = subprocess.run(
        cmd, shell=True, cwd=cwd or PROJECT_ROOT,
        capture_output=False, text=True
    )
    if check and result.returncode != 0:
        print(f"Command failed with code {result.returncode}")
        sys.exit(1)
    return result

def wait_for_job(language: str):
    """Wait for a batch job to complete and process results."""
    script = f"translate_batch_api_{language}.py"
    script_path = SCRIPTS_DIR / "translation" / script
    
    print(f"\n⏳ Waiting for {language.upper()} translation job...")
    run_command(f"python {script_path} --wait")

def main():
    print("🚀 Full Retranslation Pipeline")
    print("=" * 60)
    print("This will:")
    print("  1. Wait for Chinese translation to complete")
    print("  2. Submit and wait for Korean translation")
    print("  3. Tokenize both languages")
    print("  4. Merge all languages")
    print("  5. Build for deployment")
    print("=" * 60)
    
    # Step 1: Wait for Chinese job
    print("\n" + "="*60)
    print("STEP 1: Waiting for Chinese translation...")
    print("="*60)
    wait_for_job("chinese")
    
    # Step 2: Submit and wait for Korean job
    print("\n" + "="*60)
    print("STEP 2: Submitting Korean translation...")
    print("="*60)
    korean_script = SCRIPTS_DIR / "translation" / "translate_batch_api_korean.py"
    run_command(f"python {korean_script}")
    
    print("\n⏳ Waiting for Korean translation job...")
    time.sleep(5)  # Brief pause before checking status
    wait_for_job("korean")
    
    # Step 3: Tokenize Chinese
    print("\n" + "="*60)
    print("STEP 3: Tokenizing Chinese...")
    print("="*60)
    run_command(
        f"python {SCRIPTS_DIR}/tokenization/pretokenize_chinese.py "
        f"--input {PROJECT_ROOT}/data/translated_chinese/translations.jsonl "
        f"--output {FRONTEND_DIR}/static/data-zh -v"
    )
    
    # Step 4: Tokenize Korean
    print("\n" + "="*60)
    print("STEP 4: Tokenizing Korean...")
    print("="*60)
    run_command(
        f"python {SCRIPTS_DIR}/tokenization/pretokenize_korean.py "
        f"--input {PROJECT_ROOT}/data/translated_korean/translations.jsonl "
        f"--output {FRONTEND_DIR}/static/data-ko -v"
    )
    
    # Step 5: Merge languages
    print("\n" + "="*60)
    print("STEP 5: Merging all languages...")
    print("="*60)
    run_command(f"python {SCRIPTS_DIR}/merge_languages.py")
    
    # Step 6: Build
    print("\n" + "="*60)
    print("STEP 6: Building frontend...")
    print("="*60)
    run_command("npm run build", cwd=FRONTEND_DIR)
    
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETE!")
    print("="*60)
    print("\nTo deploy, run:")
    print("  cd frontend && npx wrangler pages deploy .svelte-kit/cloudflare --project-name duojp")

if __name__ == "__main__":
    main()

