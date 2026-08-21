import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent

# On Railway, mount a Volume and set UPLOADS_DIR to its mount path so
# notes survive redeploys. Defaults to a local folder for dev.
UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", BASE_DIR / "uploads"))
METADATA_FILE = UPLOADS_DIR / "notes.json"
STATIC_DIR = BASE_DIR / "static"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
if not METADATA_FILE.exists():
    METADATA_FILE.write_text("[]", encoding="utf-8")

app = FastAPI(title="Markdown Notes Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_metadata() -> list[dict]:
    return json.loads(METADATA_FILE.read_text(encoding="utf-8"))


def write_metadata(notes: list[dict]) -> None:
    METADATA_FILE.write_text(json.dumps(notes, indent=2), encoding="utf-8")


ALLOWED_EXTENSIONS = (".md", ".html", ".htm")


@app.post("/notes")
async def upload_note(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only .md and .html files are allowed")

    dest_path = UPLOADS_DIR / file.filename
    if dest_path.exists():
        stem, suffix = dest_path.stem, dest_path.suffix
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        dest_path = UPLOADS_DIR / f"{stem}-{timestamp}{suffix}"

    contents = await file.read()
    dest_path.write_bytes(contents)

    note = {
        "filename": dest_path.name,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(contents),
    }

    notes = read_metadata()
    notes.append(note)
    write_metadata(notes)

    return note


@app.get("/notes")
async def list_notes():
    notes = read_metadata()
    return sorted(notes, key=lambda n: n["uploaded_at"], reverse=True)


@app.get("/notes/{filename}")
async def get_note(filename: str):
    notes = read_metadata()
    note = next((n for n in notes if n["filename"] == filename), None)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note file missing on disk")

    content = file_path.read_text(encoding="utf-8")
    return {**note, "content": content}


# Serves the built frontend (frontend/dist copied here at Docker build time).
# Mounted last so it never shadows the /notes API routes above.
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
