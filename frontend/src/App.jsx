import { useEffect, useState } from "react";
import UploadForm from "./components/UploadForm.jsx";
import NotesList from "./components/NotesList.jsx";
import NoteDetail from "./components/NoteDetail.jsx";
import { fetchNotes } from "./api";

export default function App() {
  const [notes, setNotes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  function loadNotes() {
    fetchNotes()
      .then(setNotes)
      .catch((e) => setError(e.message));
  }

  useEffect(loadNotes, []);

  return (
    <div className="app">
      <h1>Markdown Notes</h1>
      {selected ? (
        <NoteDetail filename={selected} onBack={() => setSelected(null)} />
      ) : (
        <>
          <UploadForm onUploaded={loadNotes} />
          {error && <p className="error">{error}</p>}
          <NotesList notes={notes} onSelect={setSelected} />
        </>
      )}
    </div>
  );
}
