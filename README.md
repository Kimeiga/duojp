# 🇯🇵 duojp

A Duolingo-style Japanese sentence builder with drag-and-drop tiles.

**[Try the live demo →](https://duojp.pages.dev)** (coming soon)

## Features

- **Drag-and-drop tiles** to build Japanese sentences
- **216,000+ sentences** from the Tatoeba corpus
- **Serverless architecture** - deploys to Cloudflare Pages (unlimited bandwidth)
- **Morphological tokenization** using MeCab + UniDic
- **Mobile-friendly** - click or drag on any device

## Quick Start

### Run Locally

```bash
git clone https://github.com/Kimeiga/duojp.git
cd duojp/frontend
npm install
npm run dev
```

Open http://localhost:5173

### Full Development Setup

To work with the corpus data and tokenization:

```bash
# Install system dependencies (macOS)
brew install mecab

# Run the setup script (downloads ~500MB of corpus data)
./scripts/setup.sh
```

## Project Structure

```
duojp/
├── frontend/                 # SvelteKit app (deployed to Cloudflare)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte         # Main UI with drag-and-drop
│   │   │   └── api/                 # Serverless API routes
│   │   └── lib/                     # Shared components & types
│   └── static/data/                 # Pre-tokenized sentence chunks (48MB)
├── app/                      # Python modules (for local dev/processing)
│   ├── tokenize.py                  # MeCab + UniDic tokenization
│   ├── generate.py                  # Exercise generation
│   ├── grade.py                     # Answer grading
│   └── server.py                    # FastAPI server (local dev)
├── scripts/
│   ├── setup.sh                     # Download corpus data
│   └── pretokenize.py               # Pre-tokenize for deployment
└── data/                     # Corpus data (gitignored, use setup.sh)
    ├── tsv/                         # Tab-separated sentence pairs
    └── raw/                         # Downloaded zip files
```

## Tech Stack

- **Frontend**: SvelteKit 5, svelte-dnd-action
- **Deployment**: Cloudflare Pages (unlimited bandwidth, free)
- **Tokenization**: MeCab + unidic-lite
- **Data**: OPUS Tatoeba corpus (216K EN-JA sentence pairs)

## Deployment

The app is configured for Cloudflare Pages:

```bash
cd frontend
npm run build
npx wrangler pages deploy .svelte-kit/cloudflare
```

Or connect the repo to Cloudflare Pages dashboard for automatic deploys.

## License

MIT

