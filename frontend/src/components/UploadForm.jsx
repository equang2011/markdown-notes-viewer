import { useRef, useState } from "react";
import { uploadNote } from "../api";

export default function UploadForm({ onUploaded }) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".md")) {
      setError("Only .md files are allowed");
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
        {busy ? "Uploading..." : "Tap to choose a .md file or drag it here"}
        <input
          ref={inputRef}
          type="file"
          accept=".md"
          hidden
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
