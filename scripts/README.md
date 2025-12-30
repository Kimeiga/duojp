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
| `pretokenize_chinese.py` | Pre-tokenize Chinese with jieba |

### Chinese Tokenizer Choice

After comprehensive testing (see `analysis/`), **jieba** was chosen over stanza because:
- Preserves compound words (图书馆, 洗衣机, 程序员)
- Preserves person/place names (李明, 北京, 上海)
- Keeps idioms together (梦想成真)
- 62% agreement with other mainstream tokenizers (highest)

Stanza was rejected because it over-splits compounds and names.

## Analysis Scripts (`analysis/`)

| Script | Purpose |
|--------|---------|
| `compare_tokenizers.py` | Compare jieba/stanza/thulac/ltp/pkuseg |
| `analyze_tokenizer_results.py` | Analyze pairwise agreement between tokenizers |

These scripts were used to evaluate tokenizers and can be re-run if needed.

