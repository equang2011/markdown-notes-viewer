import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { fetchNote } from "../api";

export default function NoteDetail({ filename, onBack }) {
  const [note, setNote] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setNote(null);
    setError("");
    fetchNote(filename)
      .then(setNote)
      .catch((e) => setError(e.message));
  }, [filename]);

  return (
    <div>
      <button className="back-button" onClick={onBack}>
        ← Back
      </button>
      {error && <p className="error">{error}</p>}
      {!note && !error && <p>Loading...</p>}
      {note && (
        <article className="markdown-body">
          <ReactMarkdown>{note.content}</ReactMarkdown>
        </article>
      )}
    </div>
  );
}
