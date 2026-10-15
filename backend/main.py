import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

import auth
import frontmatter
import tagger

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

app.include_router(auth.router)
app.middleware("http")(auth.require_session)

# Added after the auth middleware so it sits outside it and CORS headers still
# reach 401 responses.
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
MARKDOWN_EXTENSIONS = (".md",)
DELETE_PASSWORD = os.environ.get("DELETE_PASSWORD", "")


def is_markdown(filename: str) -> bool:
    return filename.lower().endswith(MARKDOWN_EXTENSIONS)


def known_tags(notes: list[dict]) -> list[str]:
    seen: list[str] = []
    for note in notes:
        for tag in note.get("tags") or []:
            if tag not in seen:
                seen.append(tag)
    return seen


def autotag(text: str, existing: list[dict]) -> str | None:
    """Prepend an LLM-suggested frontmatter block to an untagged markdown note.

    Returns the rewritten text, or None to leave the note exactly as uploaded —
    which is also what happens on any gateway failure.
    """
    fields, body = frontmatter.split_frontmatter(text)
    if fields:
        return None  # the note already declares its own metadata; don't touch it

    suggestion = tagger.suggest(body, known_tags(existing))
    if suggestion is None:
        return None

    block = {k: v for k, v in suggestion.items() if v}
    return frontmatter.dump(block, body) if block else None


def with_defaults(note: dict) -> dict:
    """Notes uploaded before frontmatter support have no title/tags/meta."""
    return {
        **note,
        "title": note.get("title") or note["filename"],
        "tags": note.get("tags") or [],
        "meta": note.get("meta") or {},
    }


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
    notes = read_metadata()

    note = {
        "filename": dest_path.name,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(contents),
        "title": dest_path.name,
        "tags": [],
        "meta": {},
    }

    # Frontmatter lives in the stored file, which stays the source of truth; the
    # block is stripped again when the note is served.
    if is_markdown(dest_path.name):
        try:
            text = contents.decode("utf-8")
        except UnicodeDecodeError:
            text = None

        if text is not None:
            # Blocking gateway call — keep it off the event loop.
            tagged = await run_in_threadpool(autotag, text, notes)
            if tagged is not None:
                text = tagged
                contents = text.encode("utf-8")
                note["size_bytes"] = len(contents)
            fields, _ = frontmatter.parse(text, fallback_title=dest_path.name)
            note.update(fields)

    dest_path.write_bytes(contents)

    # Re-read rather than reusing the copy from before the tagging call, which
    # may have blocked for several seconds.
    notes = read_metadata()
    notes.append(note)
    write_metadata(notes)

    return note


@app.get("/notes")
async def list_notes(tag: str | None = Query(default=None)):
    notes = [with_defaults(n) for n in read_metadata()]
    if tag:
        notes = [n for n in notes if tag in n["tags"]]
    return sorted(notes, key=lambda n: n["uploaded_at"], reverse=True)


@app.get("/tags")
async def list_tags():
    """Every tag in use, with how many notes carry it."""
    counts: dict[str, int] = {}
    for note in read_metadata():
        for tag in note.get("tags") or []:
            counts[tag] = counts.get(tag, 0) + 1
    return [
        {"tag": tag, "count": count}
        for tag, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


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
    if is_markdown(filename):
        _, content = frontmatter.split_frontmatter(content)
    return {**with_defaults(note), "content": content}


@app.post("/notes/{filename}/retag")
async def retag_note(filename: str, password: str = Query(...)):
    """Re-run the tagger on a stored note and rewrite its frontmatter.

    Unlike upload, a gateway failure is an error here: the caller asked for tags
    and should be told they didn't happen. The note is left untouched.
    """
    if not DELETE_PASSWORD or password != DELETE_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    if not is_markdown(filename):
        raise HTTPException(status_code=400, detail="Only .md notes can be tagged")

    notes = read_metadata()
    if not any(n["filename"] == filename for n in notes):
        raise HTTPException(status_code=404, detail="Note not found")

    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note file missing on disk")

    text = file_path.read_text(encoding="utf-8")
    fields, body = frontmatter.split_frontmatter(text)

    others = [n for n in notes if n["filename"] != filename]
    suggestion = await run_in_threadpool(tagger.suggest, body, known_tags(others))
    if suggestion is None or not suggestion["tags"]:
        raise HTTPException(status_code=502, detail="Tagging service unavailable")

    # Keep any fields the note already declares; only tags are replaced, and the
    # title is filled in only if the note doesn't have one.
    fields["tags"] = suggestion["tags"]
    if not fields.get("title") and suggestion["title"]:
        fields["title"] = suggestion["title"]
    contents = frontmatter.dump(fields, body).encode("utf-8")
    file_path.write_bytes(contents)

    parsed, _ = frontmatter.parse(contents.decode("utf-8"), fallback_title=filename)

    # Re-read: the gateway call may have taken a while.
    notes = read_metadata()
    for n in notes:
        if n["filename"] == filename:
            n.update(parsed)
            n["size_bytes"] = len(contents)
            updated = n
    write_metadata(notes)

    return with_defaults(updated)


@app.delete("/notes/{filename}")
async def delete_note(filename: str, password: str = Query(...)):
    if not DELETE_PASSWORD or password != DELETE_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    notes = read_metadata()
    note = next((n for n in notes if n["filename"] == filename), None)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    file_path = UPLOADS_DIR / filename
    if file_path.exists():
        file_path.unlink()

    notes = [n for n in notes if n["filename"] != filename]
    write_metadata(notes)

    return {"deleted": filename}


# Serves the built frontend (frontend/dist copied here at Docker build time).
# Mounted last so it never shadows the /notes API routes above.
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
