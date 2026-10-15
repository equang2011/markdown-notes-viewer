import { useCallback, useEffect, useState } from "react";
import UploadForm from "./components/UploadForm.jsx";
import NotesList from "./components/NotesList.jsx";
import NoteDetail from "./components/NoteDetail.jsx";
import TagFilter from "./components/TagFilter.jsx";
import LockScreen from "./components/LockScreen.jsx";
import { fetchAuthStatus, fetchNotes, fetchTags, LockedError } from "./api";

export default function App() {
  const [notes, setNotes] = useState([]);
  const [tags, setTags] = useState([]);
  const [activeTag, setActiveTag] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  // null until we know; { pinLength } when the site is locked.
  const [lock, setLock] = useState(null);
  const [unlocked, setUnlocked] = useState(false);

  useEffect(() => {
    fetchAuthStatus()
      .then((s) => {
        if (s.authed) setUnlocked(true);
        else setLock({ pinLength: s.pin_length });
      })
      .catch((e) => setError(e.message));
  }, []);

  const loadNotes = useCallback(() => {
    if (!unlocked) return;
    Promise.all([fetchNotes(activeTag), fetchTags()])
      .then(([loadedNotes, loadedTags]) => {
        setNotes(loadedNotes);
        setTags(loadedTags);
      })
      .catch((e) => {
        // Session expired or cookie cleared: back to the lock screen.
        if (e instanceof LockedError) {
          setUnlocked(false);
          fetchAuthStatus().then((s) => setLock({ pinLength: s.pin_length }));
        } else {
          setError(e.message);
        }
      });
  }, [activeTag, unlocked]);

  useEffect(loadNotes, [loadNotes]);

  if (!unlocked && lock) {
    return (
      <LockScreen pinLength={lock.pinLength} onUnlocked={() => setUnlocked(true)} />
    );
  }
  if (!unlocked) {
    return <div className="app">{error && <p className="error">{error}</p>}</div>;
  }

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
