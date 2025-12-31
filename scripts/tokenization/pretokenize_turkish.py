#!/usr/bin/env python3
"""
Pre-tokenize Turkish corpus sentences and output JSON chunks for serverless deployment.

This script:
1. Reads Turkish translations JSONL file (id, en, tr)
2. Tokenizes each Turkish sentence with zeyrek
3. Merges vowel harmony allomorph pairs
4. Outputs JSON chunks (1000 sentences each)
5. Creates manifest.json with metadata
6. Creates distractors.json with common tokens for exercise generation

Zeyrek is used because it:
- Provides accurate morphological analysis for Turkish
- Properly separates suffixes from stems
- Handles vowel harmony variants
- Easy to install: pip install zeyrek

Usage:
    python scripts/tokenization/pretokenize_turkish.py --input data/translated_turkish/translations.jsonl --output frontend/static/data-tr
"""
import argparse
import json
import re
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any, Tuple

try:
    import zeyrek
except ImportError:
    print("Please install zeyrek: pip install zeyrek")
    sys.exit(1)

# Punctuation to filter out from tokens
PUNCTUATION = {
    ".", ",", ";", ":", "?", "!", "(", ")", "[", "]",
    '"', "'", "-", "–", "—", " ", "\t", "\n", "…", "...",
    "'", "'", """, """, "«", "»"
}

CHUNK_SIZE = 1000  # Sentences per chunk
NUM_DISTRACTORS = 500  # Top N tokens for distractor pool

# Turkish vowel harmony allomorph pairs
# These suffixes change form based on vowel harmony rules:
# - Front vowels (e, i, ö, ü) vs Back vowels (a, ı, o, u)
# - Rounded vs Unrounded vowels
# Format: {surface_form: (merged_form, morpheme_type)}

# Plural suffix: -ler (front) / -lar (back)
PLURAL_ALLOMORPHS = {
    "ler": ("ler/lar", "PLURAL"),
    "lar": ("ler/lar", "PLURAL"),
}

# Locative suffix: -de/-da (after voiced) / -te/-ta (after voiceless)
LOCATIVE_ALLOMORPHS = {
    "de": ("de/da", "LOC"),
    "da": ("de/da", "LOC"),
    "te": ("de/da", "LOC"),  # after voiceless consonants
    "ta": ("de/da", "LOC"),
}

# Ablative suffix: -den/-dan / -ten/-tan
ABLATIVE_ALLOMORPHS = {
    "den": ("den/dan", "ABL"),
    "dan": ("den/dan", "ABL"),
    "ten": ("den/dan", "ABL"),
    "tan": ("den/dan", "ABL"),
}

# Dative suffix: -e/-a / -ye/-ya (after vowels)
DATIVE_ALLOMORPHS = {
    "e": ("(y)e/a", "DAT"),
    "a": ("(y)e/a", "DAT"),
    "ye": ("(y)e/a", "DAT"),
    "ya": ("(y)e/a", "DAT"),
}

# Accusative suffix: -i/-ı/-u/-ü / -yi/-yı/-yu/-yü (high vowel + optional y-buffer)
ACCUSATIVE_ALLOMORPHS = {
    "i": ("(y)i/ı/u/ü", "ACC"),
    "ı": ("(y)i/ı/u/ü", "ACC"),
    "u": ("(y)i/ı/u/ü", "ACC"),
    "ü": ("(y)i/ı/u/ü", "ACC"),
    "yi": ("(y)i/ı/u/ü", "ACC"),
    "yı": ("(y)i/ı/u/ü", "ACC"),
    "yu": ("(y)i/ı/u/ü", "ACC"),
    "yü": ("(y)i/ı/u/ü", "ACC"),
}

# Genitive suffix: -in/-ın/-un/-ün / -nin/-nın/-nun/-nün (high vowel + optional n-buffer)
GENITIVE_ALLOMORPHS = {
    "in": ("(n)in/ın/un/ün", "GEN"),
    "ın": ("(n)in/ın/un/ün", "GEN"),
    "un": ("(n)in/ın/un/ün", "GEN"),
    "ün": ("(n)in/ın/un/ün", "GEN"),
    "nin": ("(n)in/ın/un/ün", "GEN"),
    "nın": ("(n)in/ın/un/ün", "GEN"),
    "nun": ("(n)in/ın/un/ün", "GEN"),
    "nün": ("(n)in/ın/un/ün", "GEN"),
}

# Past tense: -di/-dı/-du/-dü / -ti/-tı/-tu/-tü
# Also includes y-buffer forms used after vowels: -ydi/-ydı/-ydu/-ydü
PAST_TENSE_ALLOMORPHS = {
    "di": ("(y)di/dı", "PAST"),
    "dı": ("(y)di/dı", "PAST"),
    "du": ("(y)di/dı", "PAST"),
    "dü": ("(y)di/dı", "PAST"),
    "ti": ("(y)di/dı", "PAST"),
    "tı": ("(y)di/dı", "PAST"),
    "tu": ("(y)di/dı", "PAST"),
    "tü": ("(y)di/dı", "PAST"),
    # Y-buffer forms (after vowels)
    "ydi": ("(y)di/dı", "PAST"),
    "ydı": ("(y)di/dı", "PAST"),
    "ydu": ("(y)di/dı", "PAST"),
    "ydü": ("(y)di/dı", "PAST"),
}

# Future tense: -ecek/-acak
FUTURE_ALLOMORPHS = {
    "ecek": ("ecek/acak", "FUT"),
    "acak": ("ecek/acak", "FUT"),
    "eceğ": ("ecek/acak", "FUT"),
    "acağ": ("ecek/acak", "FUT"),
}

# Reported past (miş-past): -miş/-mış/-muş/-müş
REPORTED_PAST_ALLOMORPHS = {
    "miş": ("miş/mış", "NARR"),
    "mış": ("miş/mış", "NARR"),
    "muş": ("miş/mış", "NARR"),
    "müş": ("miş/mış", "NARR"),
}

# Progressive suffix: -iyor/-ıyor/-uyor/-üyor (high vowel harmony)
PROGRESSIVE_ALLOMORPHS = {
    "iyor": ("iyor/üyor", "PROG"),
    "ıyor": ("iyor/üyor", "PROG"),
    "uyor": ("iyor/üyor", "PROG"),
    "üyor": ("iyor/üyor", "PROG"),
}

# Possessive suffixes (1st person singular): -im/-ım/-um/-üm (high vowel harmony)
POSS_1S_ALLOMORPHS = {
    "im": ("im/ım/um/üm", "P1S"),
    "ım": ("im/ım/um/üm", "P1S"),
    "um": ("im/ım/um/üm", "P1S"),
    "üm": ("im/ım/um/üm", "P1S"),
}

# Conditional: -se/-sa
CONDITIONAL_ALLOMORPHS = {
    "se": ("se/sa", "COND"),
    "sa": ("se/sa", "COND"),
}

# Optative/wish: -eyim/-ayım
OPTATIVE_ALLOMORPHS = {
    "eyim": ("eyim/ayım", "OPT"),
    "ayım": ("eyim/ayım", "OPT"),
}

# Combine all allomorph dictionaries
ALL_SUFFIX_ALLOMORPHS = {}
ALL_SUFFIX_ALLOMORPHS.update(PLURAL_ALLOMORPHS)
ALL_SUFFIX_ALLOMORPHS.update(LOCATIVE_ALLOMORPHS)
ALL_SUFFIX_ALLOMORPHS.update(ABLATIVE_ALLOMORPHS)
ALL_SUFFIX_ALLOMORPHS.update(PAST_TENSE_ALLOMORPHS)
ALL_SUFFIX_ALLOMORPHS.update(FUTURE_ALLOMORPHS)
ALL_SUFFIX_ALLOMORPHS.update(REPORTED_PAST_ALLOMORPHS)
ALL_SUFFIX_ALLOMORPHS.update(PROGRESSIVE_ALLOMORPHS)
ALL_SUFFIX_ALLOMORPHS.update(CONDITIONAL_ALLOMORPHS)
ALL_SUFFIX_ALLOMORPHS.update(OPTATIVE_ALLOMORPHS)
# Note: Single-char suffixes like dative, accusative can conflict with words
# So we only apply them when explicitly detected as suffixes

# Mapping of merged allomorph forms to their standalone variants that should be filtered
ALLOMORPH_STANDALONE_FORMS = {
    "ler/lar": {"ler", "lar"},
    "de/da": {"de", "da", "te", "ta"},
    "den/dan": {"den", "dan", "ten", "tan"},
    "(y)e/a": {"ye", "ya"},  # Keep 'e', 'a' as they're common words
    "(y)i/ı/u/ü": {"yi", "yı", "yu", "yü"},  # Keep single vowels
    "(n)in/ın/un/ün": {"nin", "nın", "nun", "nün"},  # Keep simple forms
    "(y)di/dı": {"di", "dı", "du", "dü", "ti", "tı", "tu", "tü", "ydi", "ydı", "ydu", "ydü"},
    "ecek/acak": {"ecek", "acak", "eceğ", "acağ"},
    "miş/mış": {"miş", "mış", "muş", "müş"},
    "iyor/üyor": {"iyor", "ıyor", "uyor", "üyor"},
    "im/ım/um/üm": {"im", "ım", "um", "üm"},
    "se/sa": {"se", "sa"},
    "eyim/ayım": {"eyim", "ayım"},
}


def is_punctuation(text: str) -> bool:
    """Check if text is purely punctuation."""
    return all(c in PUNCTUATION for c in text)


def filter_confusing_allomorphs(tokens: List[str]) -> List[str]:
    """
    Filter out standalone allomorph forms when the merged form exists.
    """
    present_merged = set(t for t in tokens if t in ALLOMORPH_STANDALONE_FORMS)
    to_remove = set()
    for merged in present_merged:
        to_remove.update(ALLOMORPH_STANDALONE_FORMS[merged])
    return [t for t in tokens if t not in to_remove]


def create_analyzer() -> zeyrek.MorphAnalyzer:
    """Create and configure Zeyrek morphological analyzer."""
    return zeyrek.MorphAnalyzer()


def extract_morphemes_from_parse(parse) -> List[Tuple[str, str]]:
    """
    Extract surface forms and their morpheme types from a zeyrek parse.
    Returns list of (surface_form, morpheme_type) tuples.
    """
    # Parse format: "[lemma:POS] surface:POS+morpheme+morpheme..."
    formatted = parse.formatted
    morphemes = parse.morphemes

    # For simple tokenization, we focus on the lemma and key suffixes
    results = []

    # Add the lemma as the first token
    lemma = parse.lemma
    if lemma and not is_punctuation(lemma):
        results.append((lemma, "STEM"))

    # Extract suffix indicators from morphemes
    suffix_indicators = {
        "A3pl": "PLURAL",  # Plural
        "Loc": "LOC",      # Locative -de/-da
        "Abl": "ABL",      # Ablative -den/-dan
        "Dat": "DAT",      # Dative -e/-a
        "Acc": "ACC",      # Accusative -i/-ı
        "Gen": "GEN",      # Genitive -in/-ın
        "Past": "PAST",    # Past tense
        "Fut": "FUT",      # Future
        "Narr": "NARR",    # Reported past
        "P1sg": "P1S",     # 1st person singular possessive
        "P2sg": "P2S",     # 2nd person singular possessive
        "P3sg": "P3S",     # 3rd person singular possessive
        "Cond": "COND",    # Conditional
        "Opt": "OPT",      # Optative
        "Neg": "NEG",      # Negative
        "Prog1": "PROG",   # Progressive -iyor
        "Prog2": "PROG",   # Progressive -mekte
        "Aor": "AOR",      # Aorist
    }

    for morph in morphemes:
        if morph in suffix_indicators:
            results.append((morph, suffix_indicators[morph]))

    return results


def tokenize_sentence_simple(tr_text: str) -> List[str]:
    """
    Simple word-based tokenization for Turkish.
    Splits on whitespace and removes punctuation.
    """
    words = tr_text.split()
    tokens = []
    for word in words:
        # Strip punctuation from word
        clean = word.strip(''.join(PUNCTUATION))
        if clean and not is_punctuation(clean):
            tokens.append(clean)
    return tokens


# Morphemes that are pedagogically useful to split (case markers, tense, etc.)
# These are the suffixes learners need to understand
SPLIT_MORPHEME_TYPES = {
    # Case markers
    'Abl', 'Dat', 'Acc', 'Gen', 'Loc', 'Ins',
    # Plural
    'A3pl',
    # Possessives
    'P1sg', 'P2sg', 'P3sg', 'P1pl', 'P2pl', 'P3pl',
    # Tense/Aspect
    'Past', 'Narr', 'Prog1', 'Prog2', 'Aor', 'Fut',
    # Question particle
    'Ques',
    # Person markers for verbs
    'A1sg', 'A2sg', 'A1pl', 'A2pl',
}

# Morphemes to skip (implicit or not useful for learners)
SKIP_MORPHEME_TYPES = {
    'A3sg',  # 3rd person singular (unmarked)
    'Pnon',  # No possessive (unmarked)
    'Zero',  # Zero derivation
}


def tokenize_word_morphemes(analyzer: zeyrek.MorphAnalyzer, word: str) -> List[str]:
    """
    Split a Turkish word into pedagogically useful morphemes.

    Strategy:
    - Keep the stem/root together with derivational suffixes
    - Split off case markers, plural, possessives, and tense markers
    - Apply allomorph merging to common vowel harmony variants

    Returns a list of morpheme strings.
    Falls back to whole word if analysis fails.
    """
    try:
        results = analyzer.analyze(word)
        if not results or not results[0]:
            return [word]

        # Get the first (best) parse
        parses = results[0]
        if not parses:
            return [word]

        parse = parses[0]  # First parse option

        # Extract the formatted analysis to get morpheme boundaries
        # Format is like: '[kitap:Noun] kitap:Noun+lar:A3pl+ım:P1sg+ı:Acc'
        formatted = parse.formatted

        # Parse the formatted string to extract morpheme surface forms
        if ']' not in formatted:
            return [word]

        morpheme_part = formatted.split(']')[1].strip()

        # Split by + to get individual morphemes (| is for derivation, keep those together)
        # First, collapse derivational chains (split by |, keep together)
        derivation_groups = morpheme_part.split('|')

        tokens = []
        stem_parts = []  # Collect stem + derivational parts

        for group in derivation_groups:
            # Split inflectional suffixes within each group
            morpheme_strs = group.split('+')

            for m in morpheme_strs:
                if ':' not in m:
                    continue

                parts = m.split(':')
                surface = parts[0]
                morph_type = parts[1] if len(parts) > 1 else ""

                # Handle arrow notation (derivation marker)
                if '→' in morph_type:
                    morph_type = morph_type.split('→')[0]

                # Skip empty or implicit morphemes
                if not surface or morph_type in SKIP_MORPHEME_TYPES:
                    continue

                # Check if this is a splittable suffix
                if morph_type in SPLIT_MORPHEME_TYPES:
                    # First, flush any accumulated stem parts
                    if stem_parts:
                        tokens.append(''.join(stem_parts))
                        stem_parts = []

                    # Apply allomorph merging
                    merged_surface = surface
                    if surface.lower() in ALL_SUFFIX_ALLOMORPHS:
                        merged_surface = ALL_SUFFIX_ALLOMORPHS[surface.lower()][0]

                    tokens.append(merged_surface)
                else:
                    # This is part of the stem/derivational chain
                    stem_parts.append(surface)

        # Flush any remaining stem parts
        if stem_parts:
            tokens.append(''.join(stem_parts))

        # If we got tokens, return them; otherwise fall back to whole word
        if tokens:
            return tokens
        return [word]

    except Exception as e:
        # Fall back to whole word on any error
        return [word]


# Global cache for word morpheme analysis to avoid repeated expensive lookups
_word_morpheme_cache: Dict[str, List[str]] = {}


def tokenize_sentence(analyzer: zeyrek.MorphAnalyzer, tr_text: str, merge_allomorphs: bool = True) -> List[str]:
    """
    Tokenize Turkish text using morphological analysis.

    For language learning, we want to show learnable units:
    - Word stems (roots/lemmas)
    - Important suffixes that change meaning (like Korean)

    Uses zeyrek morphological analyzer to split words into morphemes.
    Uses caching to avoid repeated expensive analysis of the same words.
    """
    global _word_morpheme_cache

    words = tr_text.split()
    tokens = []

    for word in words:
        # Strip leading/trailing punctuation
        clean = word.strip(''.join(PUNCTUATION))
        if not clean or is_punctuation(clean):
            continue

        # Check cache first
        clean_lower = clean.lower()
        if clean_lower in _word_morpheme_cache:
            tokens.extend(_word_morpheme_cache[clean_lower])
            continue

        # Use morphological analysis to split word into morphemes
        morphemes = tokenize_word_morphemes(analyzer, clean)

        # Cache the result
        _word_morpheme_cache[clean_lower] = morphemes
        tokens.extend(morphemes)

    return tokens


def process_corpus(input_path: Path, output_dir: Path, verbose: bool = False, use_morphology: bool = True):
    """Process corpus and output JSON chunks."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    # Initialize morphological analyzer
    analyzer = None
    if use_morphology:
        try:
            analyzer = zeyrek.MorphAnalyzer()
            if verbose:
                print("Using zeyrek morphological analyzer")
        except Exception as e:
            print(f"Warning: Could not initialize zeyrek analyzer: {e}")
            print("Falling back to simple word tokenization")

    token_counter: Counter = Counter()
    sentences: List[Dict[str, Any]] = []
    chunk_index = 0
    total_count = 0

    if verbose:
        print(f"Reading {input_path}...")

    with open(input_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            en_text = data.get("en", "")
            tr_text = data.get("tr", "")
            sent_id = data.get("id", total_count)

            if not tr_text:
                continue

            # Handle case where tr_text is a list (some batch results)
            if isinstance(tr_text, list):
                tr_text = tr_text[0] if tr_text else ""
                if not tr_text:
                    continue

            # Use morphological tokenization if analyzer is available
            if analyzer:
                tokens = tokenize_sentence(analyzer, tr_text)
            else:
                tokens = tokenize_sentence_simple(tr_text)

            if not tokens:
                continue

            # Count tokens for distractor pool
            for t in tokens:
                token_counter[t] += 1

            sentences.append({
                "id": sent_id,
                "en": en_text,
                "tr": tr_text,
                "tokens": tokens
            })
            total_count += 1

            # Progress reporting
            if verbose and total_count % 500 == 0:
                cache_size = len(_word_morpheme_cache) if analyzer else 0
                print(f"  Processed {total_count} sentences (cache size: {cache_size})")

            # Write chunk when full
            if len(sentences) >= CHUNK_SIZE:
                chunk_path = chunks_dir / f"{chunk_index}.json"
                with open(chunk_path, "w", encoding="utf-8") as cf:
                    json.dump(sentences, cf, ensure_ascii=False)
                if verbose:
                    print(f"  Wrote chunk {chunk_index} ({len(sentences)} sentences)")
                sentences = []
                chunk_index += 1

    # Write final partial chunk
    if sentences:
        chunk_path = chunks_dir / f"{chunk_index}.json"
        with open(chunk_path, "w", encoding="utf-8") as cf:
            json.dump(sentences, cf, ensure_ascii=False)
        if verbose:
            print(f"  Wrote chunk {chunk_index} ({len(sentences)} sentences)")
        chunk_index += 1

    # Write manifest
    manifest = {
        "total": total_count,
        "chunks": chunk_index,
        "chunk_size": CHUNK_SIZE,
        "source": input_path.name,
        "language": "tr"
    }
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)
    if verbose:
        print(f"Wrote manifest: {manifest_path}")

    # Write distractors (top N most common tokens)
    top_tokens = [token for token, _ in token_counter.most_common(NUM_DISTRACTORS)]
    filtered_tokens = filter_confusing_allomorphs(top_tokens)
    distractors_path = output_dir / "distractors.json"
    with open(distractors_path, "w", encoding="utf-8") as df:
        json.dump(filtered_tokens, df, ensure_ascii=False)
    if verbose:
        removed = len(top_tokens) - len(filtered_tokens)
        print(f"Wrote distractors: {distractors_path} ({len(filtered_tokens)} tokens, {removed} confusing allomorphs removed)")

    return total_count, chunk_index


def main():
    parser = argparse.ArgumentParser(description="Pre-tokenize Turkish corpus")
    parser.add_argument("--input", "-i", required=True, help="Input JSONL file")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    total, chunks = process_corpus(input_path, output_dir, args.verbose)
    print(f"Done! Processed {total:,} sentences into {chunks} chunks")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
