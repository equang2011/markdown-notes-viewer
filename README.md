# Markdown Notes Viewer

Minimal personal markdown notes viewer. Upload `.md` files, view them in a clean list, read them rendered.

## Backend (FastAPI)

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Runs at http://localhost:8000. Uploaded files land in `backend/uploads/`, metadata in `backend/notes.json`.

## Frontend (React + Vite)

```
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173.

## Frontmatter and tags

A `.md` note may begin with an optional YAML frontmatter block:

```
---
title: Broadcasting
tags: [numpy, core]
prereqs: [NP-01, NP-02]
minutes: 75
---

# Broadcasting
...
```

- `title` replaces the filename in the list. Defaults to the filename.
- `tags` drives the tag filter above the list. Also accepts a plain
  comma-separated string (`tags: dinner, quick`).
- **Any other key is kept as-is** and shown as a small field table on the note
  page. The app doesn't interpret these, so a note can carry whatever structure
  it wants (lesson prerequisites, ticket IDs, status) without a schema change.

Notes without a block work exactly as before, as do malformed blocks — they're
left as ordinary content. The block is stripped when the note is rendered but
stays in the stored file, which remains the source of truth. Frontmatter is
parsed for `.md` only, not `.html`.

## Automatic tagging

When a `.md` file is uploaded **without** a frontmatter block, the backend asks
an LLM gateway for a title and tags, writes the block into the file, and saves
it. Notes that already declare their own frontmatter are never touched, and
`.html` files are never sent.

Set `GATEWAY_API_KEY` to enable it — with no key, uploads behave exactly as they
did before.

| Variable              | Default                                                        |
| --------------------- | -------------------------------------------------------------- |
| `GATEWAY_API_KEY`     | *(unset — tagging disabled)*                                     |
| `GATEWAY_URL`         | `https://llm-gateway-production-b085.up.railway.app/invoke`      |
| `TAGGER_MODEL`        | `deepseek/deepseek-v4-flash-0731`                                |
| `TAGGER_TIMEOUT`      | `20` (seconds)                                                   |
| `ENABLE_AUTO_TAGGING` | `1` — set to `0` to turn tagging off while keeping the key set   |

Design points worth knowing:

- **Fail-open.** Any gateway failure — timeout, 401, 502, unparseable reply —
  logs a line and saves the note untagged. Tagging never costs you an upload.
- **Tag vocabulary is fed back in.** Tags already in use are passed to the model
  with an instruction to reuse them, so the tag list converges instead of
  fragmenting into `numpy` / `NumPy` / `np-arrays`. Tags are normalized to
  lowercase-kebab and capped at 5.
- **Client-side timeout is enforced here.** The gateway has a known gap where a
  hung call isn't bounded, so `TAGGER_TIMEOUT` is the real limit. The call runs
  in a threadpool so it can't block the event loop.
- Only `title` and `tags` are generated. Structural fields like `prereqs` stay
  hand-authored — the model would invent them.
- The gateway's env vars are read at import time; restart after changing them.

## Notes

- Only `.md` and `.html` files are accepted.
- No auth, no database — metadata is a flat JSON file.
- In dev, the backend must be running on port 8000 (frontend hits it directly via `frontend/src/api.js`).

## Deploy to Railway

The `Dockerfile` builds the frontend and serves it from FastAPI as one container — one Railway service, no separate frontend deploy.

1. Push this repo to GitHub, then in Railway: **New Project → Deploy from GitHub repo**. Railway auto-detects the `Dockerfile`.
2. Add a **Volume** to the service, mounted at `/app/uploads`.
3. Add an environment variable: `UPLOADS_DIR=/app/uploads` (points the app at the volume instead of the container's ephemeral disk).
4. Deploy. Railway sets `PORT` automatically; the Dockerfile's `CMD` already binds to it.

To keep strangers out, set `SITE_PASSWORD`. The browser then asks for a login on first visit (any username, that password) and every route, API included, requires it. Unset, the site is open. `DELETE_PASSWORD` additionally gates deleting and retagging.

Uploaded notes and `notes.json` persist on the volume across redeploys. Don't scale this service to multiple replicas — the JSON metadata file isn't safe for concurrent writers.
