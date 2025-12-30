#!/usr/bin/env python3
"""
Compare different Chinese tokenizers on a comprehensive set of test sentences.
Tests: jieba, stanza, thulac, ltp, spacy-pkuseg
"""
import json
import time
from typing import List, Dict, Callable, Tuple

# Test sentences with diverse grammatical structures
TEST_SENTENCES = [
    # Basic sentences
    ("我喜欢吃苹果。", "Basic SVO"),
    ("他是我的朋友。", "Copula"),
    ("她很漂亮。", "Adjective predicate"),
    
    # 4-character idioms (成语) - KEY TEST CASES
    ("梦想成真。", "Idiom: dreams come true"),
    ("我希望我的梦想成真。", "Idiom in context"),
    ("他一心一意地学习。", "Idiom: wholeheartedly"),
    ("这件事情一目了然。", "Idiom: clear at a glance"),
    ("我们应该实事求是。", "Idiom: seek truth from facts"),
    ("他的成绩突飞猛进。", "Idiom: by leaps and bounds"),
    ("她心满意足地笑了。", "Idiom: satisfied"),
    
    # Compound words
    ("我在图书馆看书。", "Compound: library"),
    ("他是一个电脑程序员。", "Compound: computer programmer"),
    ("她买了一台洗衣机。", "Compound: washing machine"),
    ("我们要保护环境。", "Compound: environment"),
    ("人工智能正在改变世界。", "Compound: artificial intelligence"),
    
    # Names
    ("北京是中国的首都。", "Place: Beijing, China"),
    ("李明去上海出差了。", "Person + place name"),
    ("张伟和王芳结婚了。", "Two person names"),
    
    # Numbers and time
    ("我有三个苹果。", "Numbers"),
    ("会议在下午三点开始。", "Time expression"),
    
    # Questions
    ("你叫什么名字？", "Question: what"),
    ("他为什么不来？", "Question: why"),
    ("这本书多少钱？", "Question: how much"),
    
    # Aspect particles
    ("我吃过中国菜。", "Experiential: 过"),
    ("他正在看着电视。", "Progressive: 着"),
    ("她已经走了。", "Completed: 了"),
    
    # Passive/causative
    ("这本书被他借走了。", "Passive: 被"),
    ("老师让学生写作业。", "Causative: 让"),
    
    # Complex sentences  
    ("虽然他很累，但是他还是继续工作。", "Although...but"),
    ("如果明天下雨，我们就不去了。", "If...then"),
    ("因为交通堵塞，所以我迟到了。", "Because...so"),
    
    # Resultative complements
    ("我听懂了他说的话。", "Resultative: understood"),
    ("他把作业做完了。", "Resultative with 把"),
    
    # Colloquial
    ("没问题！", "Colloquial: no problem"),
    ("太棒了！", "Colloquial: awesome"),
    ("我觉得没什么大不了的。", "Colloquial: not a big deal"),
]

# Expected "ideal" tokenizations for key sentences (for scoring)
EXPECTED_TOKENIZATIONS = {
    "梦想成真。": ["梦想", "成真"],  # Should split idiom
    "我希望我的梦想成真。": ["我", "希望", "我", "的", "梦想", "成真"],
    "图书馆": ["图书馆"],  # Should NOT split
    "电脑程序员": ["电脑", "程序员"],  # Can split
    "洗衣机": ["洗衣机"],  # Should NOT split
    "人工智能": ["人工智能"],  # Should NOT split (or 人工 + 智能 ok)
    "北京": ["北京"],  # Should NOT split
    "上海": ["上海"],  # Should NOT split
}


def load_tokenizers():
    """Load all available tokenizers."""
    tokenizers = {}
    
    # 1. jieba
    try:
        import jieba
        jieba.setLogLevel(20)  # Suppress loading messages
        def jieba_tokenize(text):
            return list(jieba.cut(text))
        tokenizers['jieba'] = jieba_tokenize
        print("✓ jieba loaded")
    except ImportError:
        print("✗ jieba not available")
    
    # 2. stanza
    try:
        import stanza
        nlp = stanza.Pipeline('zh', processors='tokenize', verbose=False)
        def stanza_tokenize(text):
            doc = nlp(text)
            return [token.text for sent in doc.sentences for token in sent.tokens]
        tokenizers['stanza'] = stanza_tokenize
        print("✓ stanza loaded")
    except Exception as e:
        print(f"✗ stanza not available: {e}")
    
    # 3. thulac
    try:
        import thulac
        thu = thulac.thulac(seg_only=True)
        def thulac_tokenize(text):
            result = thu.cut(text, text=True)
            return result.split()
        tokenizers['thulac'] = thulac_tokenize
        print("✓ thulac loaded")
    except Exception as e:
        print(f"✗ thulac not available: {e}")
    
    # 4. ltp
    try:
        from ltp import LTP
        ltp = LTP('LTP/small')
        def ltp_tokenize(text):
            output = ltp.pipeline([text], tasks=['cws'])
            return output.cws[0]
        tokenizers['ltp'] = ltp_tokenize
        print("✓ ltp loaded")
    except Exception as e:
        print(f"✗ ltp not available: {e}")
    
    # 5. spacy-pkuseg
    try:
        import spacy_pkuseg as pkuseg
        seg = pkuseg.pkuseg()
        def pkuseg_tokenize(text):
            return seg.cut(text)
        tokenizers['pkuseg'] = pkuseg_tokenize
        print("✓ pkuseg loaded")
    except Exception as e:
        print(f"✗ pkuseg not available: {e}")
    
    return tokenizers


def filter_punctuation(tokens: List[str]) -> List[str]:
    """Remove punctuation tokens for cleaner comparison."""
    punct = set("。，、；：？！…—·「」『』（）【】《》""''〈〉.?,!;:()")
    return [t for t in tokens if t.strip() and t not in punct]


def run_comparison(tokenizers: Dict[str, Callable]):
    """Run all tokenizers on all test sentences."""
    results = []
    
    for sentence, description in TEST_SENTENCES:
        result = {
            'sentence': sentence,
            'description': description,
            'tokenizations': {}
        }
        
        for name, tokenize_fn in tokenizers.items():
            try:
                tokens = tokenize_fn(sentence)
                tokens_clean = filter_punctuation(tokens)
                result['tokenizations'][name] = tokens_clean
            except Exception as e:
                result['tokenizations'][name] = [f"ERROR: {e}"]
        
        results.append(result)
    
    return results


def analyze_results(results: List[Dict]) -> Dict:
    """Analyze tokenization results and score each tokenizer."""
    tokenizer_names = list(results[0]['tokenizations'].keys())
    
    # Scoring categories
    scores = {name: {
        'idiom_split': 0,      # Properly splits idioms
        'compound_preserve': 0, # Preserves compound words
        'name_preserve': 0,     # Preserves names
        'consistency': 0,       # Consistent behavior
        'total_tokens': 0,
    } for name in tokenizer_names}
    
    # Analyze idiom handling (sentences 3-10)
    idiom_sentences = [r for r in results if 'Idiom' in r['description']]
    for r in idiom_sentences:
        for name, tokens in r['tokenizations'].items():
            # Check if idioms are split (good for learning)
            token_str = ''.join(tokens)
            # Count 2-char segments vs 4-char segments
            has_2char_split = any(len(t) == 2 for t in tokens if len(t) <= 4)
            if has_2char_split:
                scores[name]['idiom_split'] += 1
    
    # Analyze compound word handling
    compound_sentences = [r for r in results if 'Compound' in r['description']]
    for r in compound_sentences:
        for name, tokens in r['tokenizations'].items():
            # Check if key compounds are preserved
            if '图书馆' in tokens:
                scores[name]['compound_preserve'] += 1
            if '洗衣机' in tokens:
                scores[name]['compound_preserve'] += 1
    
    # Analyze name handling
    name_sentences = [r for r in results if 'name' in r['description'].lower() or 'Place' in r['description']]
    for r in name_sentences:
        for name, tokens in r['tokenizations'].items():
            if '北京' in tokens:
                scores[name]['name_preserve'] += 1
            if '上海' in tokens:
                scores[name]['name_preserve'] += 1
            if '中国' in tokens:
                scores[name]['name_preserve'] += 1
    
    # Count total tokens (lower might mean better grouping)
    for r in results:
        for name, tokens in r['tokenizations'].items():
            scores[name]['total_tokens'] += len(tokens)
    
    return scores


def print_results(results: List[Dict], scores: Dict):
    """Print formatted comparison results."""
    tokenizer_names = list(results[0]['tokenizations'].keys())
    
    print("\n" + "=" * 100)
    print("TOKENIZER COMPARISON RESULTS")
    print("=" * 100)
    
    # Print each sentence's tokenization
    for r in results:
        print(f"\n📝 {r['sentence']}")
        print(f"   ({r['description']})")
        for name in tokenizer_names:
            tokens = r['tokenizations'][name]
            print(f"   {name:10}: {tokens}")
    
    # Print scores
    print("\n" + "=" * 100)
    print("SCORING SUMMARY")
    print("=" * 100)
    print(f"\n{'Tokenizer':<12} {'Idiom Split':<12} {'Compound':<12} {'Names':<12} {'Total Tokens':<12}")
    print("-" * 60)
    for name in tokenizer_names:
        s = scores[name]
        print(f"{name:<12} {s['idiom_split']:<12} {s['compound_preserve']:<12} {s['name_preserve']:<12} {s['total_tokens']:<12}")
    
    # Recommendations
    print("\n" + "=" * 100)
    print("ANALYSIS")
    print("=" * 100)
    
    # Find best for idiom splitting
    best_idiom = max(tokenizer_names, key=lambda n: scores[n]['idiom_split'])
    print(f"\n🏆 Best for splitting idioms: {best_idiom} (score: {scores[best_idiom]['idiom_split']})")
    
    # Find best for compound preservation
    best_compound = max(tokenizer_names, key=lambda n: scores[n]['compound_preserve'])
    print(f"🏆 Best for preserving compounds: {best_compound} (score: {scores[best_compound]['compound_preserve']})")
    
    # Find best for name preservation
    best_names = max(tokenizer_names, key=lambda n: scores[n]['name_preserve'])
    print(f"🏆 Best for preserving names: {best_names} (score: {scores[best_names]['name_preserve']})")


def main():
    print("Loading tokenizers...")
    print("-" * 40)
    tokenizers = load_tokenizers()
    
    if not tokenizers:
        print("No tokenizers available!")
        return
    
    print(f"\nLoaded {len(tokenizers)} tokenizers: {list(tokenizers.keys())}")
    print(f"Testing {len(TEST_SENTENCES)} sentences...")
    
    results = run_comparison(tokenizers)
    scores = analyze_results(results)
    print_results(results, scores)
    
    # Save detailed results to JSON
    output_path = '/tmp/tokenizer_comparison.json'
    with open(output_path, 'w') as f:
        json.dump({'results': results, 'scores': scores}, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    main()

