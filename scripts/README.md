# Scripts

This directory contains utility scripts for data processing, translation, and analysis.

## Directory Structure

```
scripts/
├── setup.sh                    # Download raw data files
├── translation/                # EN→JA/ZH translation scripts
├── tokenization/               # Tokenization and pre-processing
└── analysis/                   # Tokenizer comparison and analysis
```

## Setup

```bash
./scripts/setup.sh              # Downloads raw Tatoeba data
```

## Translation Scripts (`translation/`)

| Script | Purpose |
|--------|---------|
| `translate_batch_api.py` | Translate EN→JA using OpenAI Batch API |
| `translate_batch_api_chinese.py` | Translate EN→ZH using OpenAI Batch API |
| `translate_chinese_realtime.py` | Translate EN→ZH using real-time API |
| `translate_full_dataset.py` | Full dataset translation pipeline |
| `translate_missing.py` | Fill in missing translations |
| `translate_with_gemini.py` | Alternative using Google Gemini |
| `fix_and_continue.py` | Resume interrupted translation jobs |

## Tokenization Scripts (`tokenization/`)

| Script | Purpose |
|--------|---------|
| `pretokenize.py` | Pre-tokenize Japanese with MeCab/UniDic |
| `pretokenize_chinese.py` | Pre-tokenize Chinese with LTP |

### Chinese Tokenizer Choice

After comprehensive testing (see `analysis/`), **LTP** was chosen:
- Splits measure words (三 + 个, 一 + 台) - essential for learners
- Splits verb + object (看 + 书) - learners see verbs separately
- Splits adverb + adjective (很 + 漂亮) - learners see 很 means "very"
- Preserves compound nouns (图书馆, 洗衣机, 热水澡)
- Preserves names (北京, 上海, 李明)

Rejected alternatives:
- **jieba**: Over-groups (merges 一个舒服, 看书, 很漂亮) - bad for learning
- **stanza**: Over-splits compounds (图书馆→图书+馆) - bad for learning

## Analysis Scripts (`analysis/`)

| Script | Purpose |
|--------|---------|
| `compare_tokenizers.py` | Compare jieba/stanza/thulac/ltp/pkuseg |
| `analyze_tokenizer_results.py` | Analyze pairwise agreement between tokenizers |

These scripts were used to evaluate tokenizers and can be re-run if needed.

