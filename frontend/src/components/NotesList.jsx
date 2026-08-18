function formatDate(iso) {
  return new Date(iso).toLocaleString();
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export default function NotesList({ notes, onSelect }) {
  if (notes.length === 0) {
    return <p className="empty">No notes uploaded yet.</p>;
  }

  return (
    <ul className="notes-list">
      {notes.map((note) => (
        <li key={note.filename}>
          <button className="note-item" onClick={() => onSelect(note.filename)}>
            <span className="note-filename">{note.filename}</span>
            <span className="note-meta">
              {formatDate(note.uploaded_at)} · {formatSize(note.size_bytes)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
