import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import DOMPurify from "dompurify";
import { fetchNote, deleteNote } from "../api";

function isHtmlFilename(filename) {
  const name = filename.toLowerCase();
  return name.endsWith(".html") || name.endsWith(".htm");
}

function NoteHeader({ note, onSelectTag }) {
  const metaEntries = Object.entries(note.meta ?? {});
  const hasTags = note.tags?.length > 0;
  if (!hasTags && metaEntries.length === 0) return null;

  return (
    <div className="note-header">
      {hasTags && (
        <div className="note-tags">
          {note.tags.map((tag) => (
            <button
              key={tag}
              className="tag"
              onClick={() => onSelectTag?.(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}
      {metaEntries.length > 0 && (
        <dl className="note-fields">
          {metaEntries.map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

export default function NoteDetail({ filename, onBack, onSelectTag }) {
  const [note, setNote] = useState(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setNote(null);
    setError("");
    fetchNote(filename)
      .then(setNote)
      .catch((e) => setError(e.message));
  }, [filename]);

  const handleDelete = async () => {
    const password = prompt("Password to delete this note:");
    if (!password) return;

    setDeleting(true);
    try {
      await deleteNote(filename, password);
      onBack();
    } catch (e) {
      setError(e.message);
      setDeleting(false);
    }
  };

  return (
    <div>
      <div className="note-detail-header">
        <button className="back-button" onClick={onBack}>
          ← Back
        </button>
        <button
          className="delete-button"
          onClick={handleDelete}
          disabled={deleting}
        >
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {!note && !error && <p>Loading...</p>}
      {note && <NoteHeader note={note} onSelectTag={onSelectTag} />}
      {note && isHtmlFilename(note.filename) && (
        <article
          className="markdown-body"
          dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(note.content) }}
        />
      )}
      {note && !isHtmlFilename(note.filename) && (
        <article className="markdown-body">
          <ReactMarkdown>{note.content}</ReactMarkdown>
        </article>
      )}
    </div>
  );
}
