import { useState } from "react";
import { retagNote } from "../api";

function formatDate(iso) {
  return new Date(iso).toLocaleString();
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export default function NotesList({ notes, onSelect, onChanged, emptyMessage }) {
  const [busy, setBusy] = useState(null);
  const [errors, setErrors] = useState({});

  async function handleRetag(filename) {
    const password = prompt("Password to retag this note:");
    if (!password) return;

    setBusy(filename);
    setErrors((prev) => ({ ...prev, [filename]: "" }));
    try {
      await retagNote(filename, password);
      onChanged();
    } catch (e) {
      setErrors((prev) => ({ ...prev, [filename]: e.message }));
    } finally {
      setBusy(null);
    }
  }

  if (notes.length === 0) {
    return <p className="empty">{emptyMessage ?? "No notes uploaded yet."}</p>;
  }

  return (
    <ul className="notes-list">
      {notes.map((note) => (
        <li key={note.filename} className="note-row">
          <button className="note-item" onClick={() => onSelect(note.filename)}>
            <span className="note-filename">{note.title || note.filename}</span>
            <span className="note-meta">
              {formatDate(note.uploaded_at)} · {formatSize(note.size_bytes)}
            </span>
            {note.tags?.length > 0 && (
              <span className="note-tags">
                {note.tags.map((tag) => (
                  <span key={tag} className="tag tag-static">
                    {tag}
                  </span>
                ))}
              </span>
            )}
          </button>
          {note.filename.toLowerCase().endsWith(".md") && (
            <button
              className="retag-button"
              disabled={busy !== null}
              onClick={() => handleRetag(note.filename)}
            >
              {busy === note.filename
                ? "Tagging…"
                : note.tags?.length > 0
                  ? "Retag"
                  : "Tag"}
            </button>
          )}
          {errors[note.filename] && (
            <p className="error">{errors[note.filename]}</p>
          )}
        </li>
      ))}
    </ul>
  );
}
