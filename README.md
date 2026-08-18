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

## Notes

- Only `.md` files are accepted.
- No auth, no database — metadata is a flat JSON file.
- In dev, the backend must be running on port 8000 (frontend hits it directly via `frontend/src/api.js`).

## Deploy to Railway

The `Dockerfile` builds the frontend and serves it from FastAPI as one container — one Railway service, no separate frontend deploy.

1. Push this repo to GitHub, then in Railway: **New Project → Deploy from GitHub repo**. Railway auto-detects the `Dockerfile`.
2. Add a **Volume** to the service, mounted at `/app/uploads`.
3. Add an environment variable: `UPLOADS_DIR=/app/uploads` (points the app at the volume instead of the container's ephemeral disk).
4. Deploy. Railway sets `PORT` automatically; the Dockerfile's `CMD` already binds to it.

Uploaded notes and `notes.json` persist on the volume across redeploys. Don't scale this service to multiple replicas — the JSON metadata file isn't safe for concurrent writers.
