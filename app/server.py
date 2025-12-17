"""
FastAPI server for Duolingo-style Japanese sentence builder.
"""
import argparse
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .dataset import Database, set_database
from .generate import get_exercise, get_exercise_by_id
from .grade import grade

app = FastAPI(title="Japanese Sentence Builder", version="1.0.0")

# Global database reference
_db: Optional[Database] = None


class GradeRequest(BaseModel):
    """Request body for grading."""
    exercise_id: int
    answer: str


class GradeResponse(BaseModel):
    """Response body for grading."""
    correct: bool
    submitted: str
    expected: str


@app.get("/exercise")
def get_new_exercise(seed: Optional[int] = None):
    """Get a new random exercise."""
    exercise = get_exercise(db=_db, seed=seed)
    if not exercise:
        raise HTTPException(status_code=404, detail="No exercises available")
    return exercise.to_dict()


@app.get("/exercise/{exercise_id}")
def get_specific_exercise(exercise_id: int):
    """Get a specific exercise by sentence ID."""
    exercise = get_exercise_by_id(exercise_id, db=_db)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise.to_dict()


@app.post("/grade", response_model=GradeResponse)
def grade_answer(request: GradeRequest):
    """Grade a user's answer."""
    # Get the exercise to get canonical answer
    exercise = get_exercise_by_id(request.exercise_id, db=_db)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    result = grade(request.answer, exercise.canonical_answer)
    return GradeResponse(
        correct=result.correct,
        submitted=result.user_answer_normalized,
        expected=result.expected_normalized
    )


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the main HTML page."""
    return HTML_PAGE


# HTML/CSS/JS frontend
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Japanese Sentence Builder</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px; margin: 0 auto; padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #58cc02; text-align: center; }
        .card { background: white; border-radius: 16px; padding: 24px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .prompt { font-size: 1.5em; margin-bottom: 20px; color: #333; }
        .answer-area { 
            min-height: 60px; padding: 16px; border: 2px dashed #ddd;
            border-radius: 12px; margin-bottom: 20px; display: flex;
            flex-wrap: wrap; gap: 8px; align-items: center;
        }
        .tiles { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
        .tile {
            background: #fff; border: 2px solid #e5e5e5; border-radius: 12px;
            padding: 12px 20px; font-size: 1.2em; cursor: pointer;
            transition: all 0.2s; user-select: none;
        }
        .tile:hover { border-color: #58cc02; transform: translateY(-2px); }
        .tile.selected { background: #58cc02; color: white; border-color: #58cc02; }
        .tile.used { opacity: 0.3; pointer-events: none; }
        .btn {
            background: #58cc02; color: white; border: none; border-radius: 12px;
            padding: 14px 32px; font-size: 1.1em; cursor: pointer;
            transition: background 0.2s; margin-right: 10px;
        }
        .btn:hover { background: #46a302; }
        .btn.secondary { background: #e5e5e5; color: #333; }
        .btn.secondary:hover { background: #ddd; }
        .result { padding: 20px; border-radius: 12px; margin-top: 20px; }
        .result.correct { background: #d7ffb8; color: #2e7d32; }
        .result.incorrect { background: #ffdede; color: #c62828; }
        .result h3 { margin: 0 0 10px 0; }
        .loading { text-align: center; color: #666; font-style: italic; }
    </style>
</head>
<body>
    <h1>🇯🇵 Japanese Sentence Builder</h1>
    <div id="app" class="card">
        <div class="loading">Loading exercise...</div>
    </div>
    <script>
        let currentExercise = null;
        let selectedTiles = [];
        let usedIndices = new Set();
        
        async function loadExercise() {
            const app = document.getElementById('app');
            app.innerHTML = '<div class="loading">Loading...</div>';
            try {
                const res = await fetch('/exercise');
                currentExercise = await res.json();
                selectedTiles = [];
                usedIndices = new Set();
                renderExercise();
            } catch (e) {
                app.innerHTML = '<div class="loading">Error loading exercise. Make sure data is ingested.</div>';
            }
        }

        function renderExercise() {
            const app = document.getElementById('app');
            app.innerHTML = `
                <div class="prompt">${currentExercise.english}</div>
                <div class="answer-area" id="answer">${selectedTiles.length === 0 ? '<span style="color:#999">Click tiles to build your answer...</span>' : ''}</div>
                <div class="tiles" id="tiles"></div>
                <button class="btn" onclick="submitAnswer()">Check</button>
                <button class="btn secondary" onclick="clearAnswer()">Clear</button>
                <button class="btn secondary" onclick="loadExercise()">Skip</button>
                <div id="result"></div>
            `;
            renderTiles();
            renderAnswer();
        }

        function renderTiles() {
            const container = document.getElementById('tiles');
            container.innerHTML = currentExercise.tiles.map((tile, i) =>
                `<span class="tile ${usedIndices.has(i) ? 'used' : ''}" onclick="selectTile(${i})">${tile}</span>`
            ).join('');
        }

        function renderAnswer() {
            const container = document.getElementById('answer');
            if (selectedTiles.length === 0) {
                container.innerHTML = '<span style="color:#999">Click tiles to build your answer...</span>';
            } else {
                container.innerHTML = selectedTiles.map((t, i) =>
                    `<span class="tile selected" onclick="unselectTile(${i})">${t.text}</span>`
                ).join('');
            }
        }

        function selectTile(index) {
            if (usedIndices.has(index)) return;
            usedIndices.add(index);
            selectedTiles.push({ text: currentExercise.tiles[index], index });
            renderTiles();
            renderAnswer();
        }

        function unselectTile(answerIndex) {
            const tile = selectedTiles[answerIndex];
            usedIndices.delete(tile.index);
            selectedTiles.splice(answerIndex, 1);
            renderTiles();
            renderAnswer();
        }

        function clearAnswer() {
            selectedTiles = [];
            usedIndices = new Set();
            renderTiles();
            renderAnswer();
            document.getElementById('result').innerHTML = '';
        }

        async function submitAnswer() {
            const answer = selectedTiles.map(t => t.text).join('');
            const res = await fetch('/grade', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ exercise_id: currentExercise.id, answer })
            });
            const result = await res.json();
            const resultDiv = document.getElementById('result');
            if (result.correct) {
                resultDiv.innerHTML = `<div class="result correct"><h3>✓ Correct!</h3></div>`;
                setTimeout(loadExercise, 1500);
            } else {
                resultDiv.innerHTML = `<div class="result incorrect"><h3>✗ Not quite</h3><p>Expected: ${result.expected}</p><p>Your answer: ${result.your_answer}</p></div>`;
            }
        }

        loadExercise();
    </script>
</body>
</html>
"""


def init_db(db_path: Path) -> Database:
    """Initialize database connection."""
    global _db
    _db = Database(db_path)
    set_database(_db)
    return _db


def main():
    import uvicorn
    
    parser = argparse.ArgumentParser(description="Run Japanese Sentence Builder server")
    parser.add_argument("--db", type=Path, default=Path("data/app.db"), help="SQLite database path")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    
    args = parser.parse_args()
    
    if not args.db.exists():
        print(f"Error: Database not found: {args.db}")
        print("Run: python -m app.ingest --tsv data/tatoeba_en_ja.tsv --db data/app.db")
        return 1
    
    init_db(args.db)
    print(f"Starting server at http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

