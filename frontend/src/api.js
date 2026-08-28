// In dev, hits the local backend directly. In production (Docker build),
// VITE_API_BASE is set to "" so requests are relative (same-origin as the
// backend, which serves both the API and the built frontend).
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function fetchNotes(tag) {
  const query = tag ? `?tag=${encodeURIComponent(tag)}` : "";
  const res = await fetch(`${API_BASE}/notes${query}`);
  if (!res.ok) throw new Error("Failed to load notes");
  return res.json();
}

export async function fetchTags() {
  const res = await fetch(`${API_BASE}/tags`);
  if (!res.ok) throw new Error("Failed to load tags");
  return res.json();
}

export async function fetchNote(filename) {
  const res = await fetch(`${API_BASE}/notes/${encodeURIComponent(filename)}`);
  if (!res.ok) throw new Error("Failed to load note");
  return res.json();
}

export async function uploadNote(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/notes`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}
