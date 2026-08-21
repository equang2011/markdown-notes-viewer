import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import DOMPurify from "dompurify";
import { fetchNote } from "../api";

function isHtmlFilename(filename) {
  const name = filename.toLowerCase();
  return name.endsWith(".html") || name.endsWith(".htm");
}

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
