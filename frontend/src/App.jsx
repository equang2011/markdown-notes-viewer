import { useCallback, useEffect, useState } from "react";
import UploadForm from "./components/UploadForm.jsx";
import NotesList from "./components/NotesList.jsx";
import NoteDetail from "./components/NoteDetail.jsx";
import TagFilter from "./components/TagFilter.jsx";
import { fetchNotes, fetchTags } from "./api";

export default function App() {
  const [notes, setNotes] = useState([]);
  const [tags, setTags] = useState([]);
  const [activeTag, setActiveTag] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  const loadNotes = useCallback(() => {
    Promise.all([fetchNotes(activeTag), fetchTags()])
      .then(([loadedNotes, loadedTags]) => {
        setNotes(loadedNotes);
        setTags(loadedTags);
      })
      .catch((e) => setError(e.message));
  }, [activeTag]);

  useEffect(loadNotes, [loadNotes]);

  return (
    <div className="app">
      <h1>Markdown Notes</h1>
      {selected ? (
        <NoteDetail
          filename={selected}
          onBack={() => setSelected(null)}
          onSelectTag={(tag) => {
            setActiveTag(tag);
            setSelected(null);
          }}
        />
      ) : (
        <>
          <UploadForm onUploaded={loadNotes} />
          {error && <p className="error">{error}</p>}
          <TagFilter tags={tags} active={activeTag} onChange={setActiveTag} />
          <NotesList
            notes={notes}
            onSelect={setSelected}
            onChanged={loadNotes}
            emptyMessage={
              activeTag ? `No notes tagged "${activeTag}".` : undefined
            }
          />
        </>
      )}
    </div>
  );
}
