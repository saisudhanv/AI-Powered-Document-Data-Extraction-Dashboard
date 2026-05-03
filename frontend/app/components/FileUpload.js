"use client";
import { useRef, useState } from "react";

const ALLOWED = ".png,.jpg,.jpeg,.pdf,.webp,.bmp,.tiff";

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function fileIcon(name) {
  return name?.toLowerCase().endsWith(".pdf") ? "📑" : "🖼️";
}

export default function FileUpload({ onUpload, uploading }) {
  const inputRef = useRef(null);
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);

  const addFiles = (newFiles) => {
    const arr = Array.from(newFiles);
    setFiles((prev) => [...prev, ...arr]);
  };

  const removeFile = (idx) => setFiles((prev) => prev.filter((_, i) => i !== idx));

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  };

  const handleSubmit = () => {
    if (files.length === 0) return;
    onUpload(files);
    setFiles([]);
  };

  return (
    <div className="upload-section">
      <h2 className="section-title">
        <span className="icon">📤</span> Upload Documents
      </h2>

      <div
        className={`upload-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <div className="upload-zone-content">
          <div className="upload-icon">☁️</div>
          <p className="upload-text">
            Drag & drop documents here or <span>browse files</span>
          </p>
          <p className="upload-hint">
            Supports PNG, JPG, PDF, WebP, BMP, TIFF — Max 10 MB per file
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          className="upload-input"
          accept={ALLOWED}
          multiple
          onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
        />
      </div>

      {files.length > 0 && (
        <>
          <div className="file-queue">
            {files.map((f, i) => (
              <div className="file-queue-item" key={i}>
                <span className="file-queue-icon">{fileIcon(f.name)}</span>
                <div className="file-queue-info">
                  <div className="file-queue-name">{f.name}</div>
                  <div className="file-queue-size">{formatSize(f.size)}</div>
                </div>
                <button
                  className="file-queue-remove"
                  onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                  title="Remove file"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <button
            className={`upload-btn ${uploading ? "uploading" : ""}`}
            onClick={handleSubmit}
            disabled={uploading}
          >
            {uploading ? "⏳ Uploading..." : `🚀 Extract Data (${files.length} file${files.length > 1 ? "s" : ""})`}
          </button>
        </>
      )}
    </div>
  );
}
