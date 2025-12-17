#!/bin/bash
# Setup script for duojp - downloads corpus data and prepares the environment
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data"

echo "🇯🇵 Setting up duojp..."
echo ""

# Create directories
mkdir -p "$DATA_DIR/raw" "$DATA_DIR/tsv"

# OPUS corpus URLs
declare -A CORPORA=(
    ["tatoeba"]="https://object.pouta.csc.fi/OPUS-Tatoeba/v2024-07-01/moses/en-ja.txt.zip"
    ["jesc"]="https://object.pouta.csc.fi/OPUS-JESC/v1/moses/en-ja.txt.zip"
    ["ted2020"]="https://object.pouta.csc.fi/OPUS-TED2020/v1/moses/en-ja.txt.zip"
    ["kftt"]="https://object.pouta.csc.fi/OPUS-KFTT/v1.1/moses/en-ja.txt.zip"
    ["qed"]="https://object.pouta.csc.fi/OPUS-QED/v2.0a/moses/en-ja.txt.zip"
)

echo "📥 Downloading OPUS corpora..."
echo ""

for name in "${!CORPORA[@]}"; do
    url="${CORPORA[$name]}"
    zip_file="$DATA_DIR/raw/${name}_en_ja.zip"
    
    if [ -f "$zip_file" ]; then
        echo "  ✓ $name already downloaded"
    else
        echo "  ⬇️  Downloading $name..."
        curl -L -o "$zip_file" "$url"
    fi
done

echo ""
echo "📦 Extracting and converting to TSV..."
echo ""

for name in "${!CORPORA[@]}"; do
    zip_file="$DATA_DIR/raw/${name}_en_ja.zip"
    tsv_file="$DATA_DIR/tsv/${name}_en_ja.tsv"
    
    if [ -f "$tsv_file" ]; then
        echo "  ✓ $name.tsv already exists"
    else
        echo "  📄 Processing $name..."
        
        # Extract to temp directory
        temp_dir=$(mktemp -d)
        unzip -q "$zip_file" -d "$temp_dir"
        
        # Find the EN and JA files
        en_file=$(find "$temp_dir" -name "*.en" | head -1)
        ja_file=$(find "$temp_dir" -name "*.ja" | head -1)
        
        if [ -f "$en_file" ] && [ -f "$ja_file" ]; then
            # Combine into TSV
            paste "$en_file" "$ja_file" > "$tsv_file"
            echo "    Created $tsv_file ($(wc -l < "$tsv_file" | tr -d ' ') lines)"
        else
            echo "    ⚠️  Could not find en/ja files in $name"
        fi
        
        rm -rf "$temp_dir"
    fi
done

echo ""
echo "🔧 Installing Python dependencies..."
pip install -q MeCab unidic-lite

echo ""
echo "📦 Installing frontend dependencies..."
cd "$PROJECT_ROOT/frontend"
npm install

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the app locally:"
echo "  cd frontend && npm run dev"
echo ""
echo "To pre-tokenize a corpus (for deployment):"
echo "  python scripts/pretokenize.py --input data/tsv/tatoeba_en_ja.tsv --output frontend/static/data -v"

