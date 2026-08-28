import { useRef, useState } from "react";
import { uploadNote } from "../api";

export default function UploadForm({ onUploaded }) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  const ALLOWED_EXTENSIONS = [".md", ".html", ".htm"];

  async function handleFile(file) {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
      setError("Only .md and .html files are allowed");
      return;
    }
    setError("");
    setBusy(true);
    try {
      await uploadNote(file);
      onUploaded();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div>
      <div
        className={`dropzone ${isDragging ? "dropzone-active" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFile(e.dataTransfer.files[0]);
        }}
      >
        {busy
          ? "Uploading and tagging..."
          : "Tap to choose a .md or .html file or drag it here"}
        <input
          ref={inputRef}
          type="file"
          accept=".md,.html,.htm"
          hidden
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
