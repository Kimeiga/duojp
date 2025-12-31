#!/usr/bin/env python3
"""
Pre-tokenize Korean corpus sentences and output JSON chunks for serverless deployment.

This script:
1. Reads Korean translations JSONL file (id, en, ko)
2. Tokenizes each Korean sentence with Kiwi (kiwipiepy)
3. Outputs JSON chunks (1000 sentences each)
4. Creates manifest.json with metadata
5. Creates distractors.json with common tokens for exercise generation

Kiwi (kiwipiepy) is used because it:
- Provides accurate morphological analysis for Korean
- Properly separates particles (조사) from stems - essential for language learners
- Handles Western transliterated names well
- Is fast and actively maintained
- Easy to install: pip install kiwipiepy

For language learning, we extract surface forms (형태소) that are meaningful units.
We keep particles separate so learners can understand Korean grammar structure.

Usage:
    python scripts/tokenization/pretokenize_korean.py --input data/translated_korean/translations.jsonl --output frontend/static/data-ko
"""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

try:
    from kiwipiepy import Kiwi
except ImportError:
    print("Please install kiwipiepy: pip install kiwipiepy")
    sys.exit(1)

# Punctuation to filter out from tokens (Korean + general)
PUNCTUATION = {
    # Korean punctuation
    "。", "，", "、", "；", "：", "？", "！", "…", "—", "·",
    "「", "」", "『", "』", "（", "）", "【", "】", "《", "》",
    """, """, "'", "'", "〈", "〉",
    # General punctuation
    ".", ",", ";", ":", "?", "!", "(", ")", "[", "]",
    '"', "'", "-", "–", "—", " ", "　", "\t", "\n"
}

# Korean transliterations of common Western names
# These are useful for validation and potential post-processing
PROPER_NOUNS_KO = {
    # Common names
    "톰", "메리", "마리", "잭", "존", "빌", "밥", "마이크", "마이클",
    "제인", "수", "앤", "앤디", "피터", "폴", "제임스", "데이빗", "데이비드",
    "사라", "케이트", "리사", "엠마", "올리비아", "노아", "리암",
    "윌리엄", "벤자민", "헨리", "알렉스", "크리스", "다니엘",
    "소피아", "이사벨라", "아바", "샬럿", "아멜리아", "하퍼",
    "제임스", "윌리엄", "벤자민", "루카스", "메이슨", "이단",
    "조지", "에드워드", "찰스", "해리", "윌리엄", "아서",
    # Places
    "뉴욕", "런던", "파리", "도쿄", "베이징", "상하이", "시드니",
    "로스앤젤레스", "시카고", "보스턴", "시애틀", "마이애미",
    "프랑스", "독일", "이탈리아", "스페인", "영국", "미국",
    "캐나다", "호주", "일본", "중국", "한국", "브라질",
}

CHUNK_SIZE = 1000  # Sentences per chunk
NUM_DISTRACTORS = 500  # Top N tokens for distractor pool

# Korean particle allomorph pairs (consonant-final form, vowel-final form)
# These particles change form based on whether the preceding syllable ends in a consonant (받침)
# Format: {surface_form: merged_form}
PARTICLE_ALLOMORPHS = {
    # Subject marker (JKS): 이 after consonant, 가 after vowel
    "이": ("이/가", "JKS"),
    "가": ("이/가", "JKS"),
    # Object marker (JKO): 을 after consonant, 를 after vowel
    "을": ("을/를", "JKO"),
    "를": ("을/를", "JKO"),
    # Topic marker (JX): 은 after consonant, 는 after vowel
    "은": ("은/는", "JX"),
    "는": ("은/는", "JX"),
    # Comitative/Conjunctive (JKB): 과 after consonant, 와 after vowel
    "과": ("과/와", "JKB"),
    "와": ("과/와", "JKB"),
    # Instrumental/Directional (JKB): 으로 after consonant (not ㄹ), 로 after vowel or ㄹ
    "으로": ("(으)로", "JKB"),
    "로": ("(으)로", "JKB"),
    # Vocative (JKV): 아 after consonant, 야 after vowel
    "아": ("아/야", "JKV"),
    "야": ("아/야", "JKV"),
    # Copula/Quotative forms - these are common in speech
    "이랑": ("(이)랑", "JKB"),
    "랑": ("(이)랑", "JKB"),
    "이나": ("(이)나", "JX"),
    "나": ("(이)나", "JX"),  # Note: 나 as pronoun is NP, not JX
    "이라고": ("(이)라고", "JKQ"),
    "라고": ("(이)라고", "JKQ"),
    "이라": ("(이)라", "JKQ"),
    "라": ("(이)라", "JKQ"),
}

# POS tags that indicate the token is a particle (조사)
PARTICLE_POS_TAGS = {
    "JKS",  # 주격 조사 (subject marker)
    "JKO",  # 목적격 조사 (object marker)
    "JKB",  # 부사격 조사 (adverbial particle)
    "JKV",  # 호격 조사 (vocative)
    "JKC",  # 보격 조사 (complement marker)
    "JKG",  # 관형격 조사 (genitive)
    "JKQ",  # 인용격 조사 (quotative)
    "JX",   # 보조사 (auxiliary particle)
    "JC",   # 접속 조사 (conjunctive)
}

# Verb ending allomorphs based on vowel harmony (아/어 alternation)
# These endings change form based on the verb stem's last vowel:
# - Bright vowels (양성모음: ㅏ, ㅗ) → 아-based endings
# - Dark vowels (음성모음: ㅓ, ㅜ, ㅡ, ㅣ, etc.) → 어-based endings
# - 하다 verbs → 여 (which contracts to 해)
# Note: Kiwi normalizes most of these to the 어-form, so we show both
# Format: {surface_form: (merged_form, pos_tag)}
VOWEL_HARMONY_ALLOMORPHS = {
    # Past tense marker (EP): 았 after bright vowels, 었 after dark vowels
    "았": ("았/었", "EP"),
    "었": ("았/었", "EP"),
    # Connective/informal (EF/EC): 아 after bright, 어 after dark
    "아": ("아/어", "EF"),
    "어": ("아/어", "EF"),
    # Polite informal ending
    "아요": ("아/어요", "EF"),
    "어요": ("아/어요", "EF"),
    # Causal/sequential connective
    "아서": ("아/어서", "EC"),
    "어서": ("아/어서", "EC"),
    # Conditional (even if)
    "아도": ("아/어도", "EC"),
    "어도": ("아/어도", "EC"),
    # Obligation (must)
    "아야": ("아/어야", "EC"),
    "어야": ("아/어야", "EC"),
    # Try doing / experience
    "아보": ("아/어 보", "EC"),
    "어보": ("아/어 보", "EC"),
    # Progressive/resultative
    "아지": ("아/어지", "EC"),
    "어지": ("아/어지", "EC"),
    # Give/receive benefit
    "아주": ("아/어 주", "EC"),
    "어주": ("아/어 주", "EC"),
    # Keep doing
    "아가": ("아/어 가", "EC"),
    "어가": ("아/어 가", "EC"),
    # Come to do
    "아오": ("아/어 오", "EC"),
    "어오": ("아/어 오", "EC"),
    # Imperative (command)
    "아라": ("아/어라", "EF"),
    "어라": ("아/어라", "EF"),
}

# Verb ending allomorphs based on consonant/vowel stem (으 insertion)
# These endings insert 으 when the verb stem ends in a consonant
# Format: {surface_form: (merged_form, pos_tag)}
CONSONANT_STEM_ALLOMORPHS = {
    # Conditional (으)면: 면 after vowel stem, 으면 after consonant stem
    "면": ("(으)면", "EC"),
    "으면": ("(으)면", "EC"),
    # Causal (으)니까: 니까 after vowel, 으니까 after consonant
    "니까": ("(으)니까", "EC"),
    "으니까": ("(으)니까", "EC"),
    # While/and (으)며
    "며": ("(으)며", "EC"),
    "으며": ("(으)며", "EC"),
    # Purpose (으)러: going to do something
    "러": ("(으)러", "EC"),
    "으러": ("(으)러", "EC"),
    # Intention (으)려고: intending to
    "려고": ("(으)려고", "EC"),
    "으려고": ("(으)려고", "EC"),
    # Ability/condition (으)ㄹ 수: can/able to
    # Note: ㄹ/을 are handled separately as adnominal endings
}

# Adnominal (관형형) ending allomorphs - modify nouns
# These are very common: "the X that..." patterns
# Format: {surface_form: (merged_form, pos_tag)}
ADNOMINAL_ALLOMORPHS = {
    # Prospective/future adnominal: ㄹ after vowel, 을 after consonant
    # "갈 것" (thing that will go), "먹을 것" (thing that will eat)
    "ᆯ": ("(으)ㄹ", "ETM"),  # Kiwi uses jongseong ᆯ (U+11AF)
    "을": ("(으)ㄹ", "ETM"),
    # Past/completed adnominal: ㄴ after vowel, 은 after consonant
    # "간 사람" (person who went), "먹은 음식" (food that was eaten)
    "ᆫ": ("(으)ㄴ", "ETM"),  # Kiwi uses jongseong ᆫ (U+11AB)
    "ㄴ": ("(으)ㄴ", "ETM"),  # Standard form just in case
    "은": ("(으)ㄴ", "ETM"),
}

# Copula (이다) ending allomorphs
# The copula "이다" (to be) has allomorphs based on the preceding noun
# Format: {surface_form: (merged_form, pos_tag)}
COPULA_ALLOMORPHS = {
    # Polite copula: 이에요 after consonant, 예요 after vowel
    "에요": ("(이)에요", "EF"),
    "예요": ("(이)에요", "EF"),
}

# POS tags for verb endings
VERB_ENDING_POS_TAGS = {
    "EF",   # 종결 어미 (sentence-final ending)
    "EC",   # 연결 어미 (connective ending)
    "EP",   # 선어말 어미 (pre-final ending, e.g., past tense)
    "ETM",  # 관형형 전성 어미 (adnominal ending)
}


def is_punctuation(text: str) -> bool:
    """Check if text is purely punctuation."""
    return all(c in PUNCTUATION for c in text)


# Mapping of merged allomorph forms to their standalone variants that should be filtered
# When the merged form exists in distractors, remove the standalone forms to reduce confusion
ALLOMORPH_STANDALONE_FORMS = {
    "이/가": {"이", "가"},
    "을/를": {"을", "를"},
    "은/는": {"은", "는"},
    "과/와": {"과", "와"},
    "(으)로": {"으로", "로"},
    "아/야": {"아", "야"},
    "(이)랑": {"이랑", "랑"},
    "(이)나": {"이나"},  # 나 alone is often pronoun "I", keep it
    "(이)라고": {"이라고", "라고"},
    "(이)라": {"이라", "라"},
    "았/었": {"았", "었"},
    "아/어": {"아", "어"},
    "아/어요": {"아요", "어요"},
    "아/어서": {"아서", "어서"},
    "아/어도": {"아도", "어도"},
    "아/어야": {"아야", "어야"},
    "아/어 보": {"아보", "어보"},
    "아/어지": {"아지", "어지"},
    "아/어 주": {"아주", "어주"},
    "아/어 가": {"아가", "어가"},
    "아/어 오": {"아오", "어오"},
    "아/어라": {"아라", "어라"},
    "(으)면": {"면", "으면"},
    "(으)니까": {"니까", "으니까"},
    "(으)며": {"며", "으며"},
    "(으)러": {"러", "으러"},
    "(으)려고": {"려고", "으려고"},
    "(으)ㄹ": {"ᆯ", "을"},
    "(으)ㄴ": {"ᆫ", "ㄴ"},  # Note: 은 can also be topic marker, handled by 은/는
    "(이)에요": {"에요", "예요"},
}


def filter_confusing_allomorphs(tokens: List[str]) -> List[str]:
    """
    Filter out standalone allomorph forms when the merged form exists.

    For example, if '은/는' is in the token list, remove standalone '은' and '는'
    to reduce confusion for learners seeing both forms as separate options.
    """
    # Find which merged forms are present
    present_merged = set(t for t in tokens if t in ALLOMORPH_STANDALONE_FORMS)

    # Collect all standalone forms that should be removed
    to_remove = set()
    for merged in present_merged:
        to_remove.update(ALLOMORPH_STANDALONE_FORMS[merged])

    # Filter out the confusing standalone forms
    return [t for t in tokens if t not in to_remove]


def create_tokenizer() -> Kiwi:
    """Create and configure Kiwi tokenizer."""
    kiwi = Kiwi()
    return kiwi


def tokenize_sentence(kiwi: Kiwi, ko_text: str, merge_allomorphs: bool = True) -> List[str]:
    """
    Tokenize Korean text and return list of surface forms (no punctuation).

    Uses Kiwi's morphological analysis. We extract surface forms that are
    meaningful for language learners. Particles are kept separate.

    When merge_allomorphs=True (default), allomorphs are merged to help learners:
    1. Particle allomorphs: "이/가", "을/를", "은/는" (consonant/vowel based)
    2. Vowel harmony endings: "았/었", "아/어요" (bright/dark vowel based)
    3. Consonant stem endings: "(으)면", "(으)니까" (consonant stem insertion)
    4. Adnominal endings: "(으)ㄹ", "(으)ㄴ" (noun-modifying forms)
    5. Copula endings: "(이)에요" (after noun)

    We use POS tags to ensure we only merge actual particles/endings, avoiding
    collisions with homographs (e.g., 가 as verb stem vs 가 as particle).
    """
    try:
        tokens = kiwi.tokenize(ko_text)
        # Extract surface forms, filter punctuation and whitespace
        result = []
        for token in tokens:
            form = token.form.strip()
            if not form or is_punctuation(form):
                continue

            if merge_allomorphs:
                tag = token.tag
                merged = False

                # Check particle allomorphs (highest priority for particles)
                if form in PARTICLE_ALLOMORPHS and tag in PARTICLE_POS_TAGS:
                    form = PARTICLE_ALLOMORPHS[form][0]
                    merged = True

                # Check vowel harmony verb endings (아/어 alternation)
                if not merged and form in VOWEL_HARMONY_ALLOMORPHS and tag in VERB_ENDING_POS_TAGS:
                    form = VOWEL_HARMONY_ALLOMORPHS[form][0]
                    merged = True

                # Check consonant stem endings (으 insertion)
                if not merged and form in CONSONANT_STEM_ALLOMORPHS and tag in VERB_ENDING_POS_TAGS:
                    form = CONSONANT_STEM_ALLOMORPHS[form][0]
                    merged = True

                # Check adnominal endings (noun-modifying forms)
                if not merged and form in ADNOMINAL_ALLOMORPHS and tag == "ETM":
                    form = ADNOMINAL_ALLOMORPHS[form][0]
                    merged = True

                # Check copula endings
                if not merged and form in COPULA_ALLOMORPHS and tag == "EF":
                    form = COPULA_ALLOMORPHS[form][0]
                    merged = True

            result.append(form)
        return result
    except Exception as e:
        print(f"Warning: Tokenization error for '{ko_text}': {e}")
        return []


def process_corpus(input_path: Path, output_dir: Path, verbose: bool = False):
    """Process corpus and output JSON chunks."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    
    # Initialize tokenizer
    if verbose:
        print("Initializing Kiwi tokenizer...")
    kiwi = create_tokenizer()
    
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
            ko_text = data.get("ko", "")
            sent_id = data.get("id", total_count)
            
            if not ko_text:
                continue
            
            # Tokenize Korean
            tokens = tokenize_sentence(kiwi, ko_text)
            
            if not tokens:
                continue  # Skip empty tokenizations
            
            # Count tokens for distractor pool
            for t in tokens:
                token_counter[t] += 1
            
            sentences.append({
                "id": sent_id,
                "en": en_text,
                "ko": ko_text,
                "tokens": tokens
            })
            total_count += 1

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
        "language": "ko"
    }
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)
    if verbose:
        print(f"Wrote manifest: {manifest_path}")

    # Write distractors (top N most common tokens)
    # Filter out standalone allomorph forms to reduce learner confusion
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
    parser = argparse.ArgumentParser(description="Pre-tokenize Korean corpus")
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

