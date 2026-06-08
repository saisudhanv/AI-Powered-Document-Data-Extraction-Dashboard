"use client";
import { useState } from "react";
import StatusBadge from "./StatusBadge";
import ConfidenceBar from "./ConfidenceBar";
import ProgressBar from "./ProgressBar";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DocumentCard({ doc, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [editFields, setEditFields] = useState([]);
  const [retrying, setRetrying] = useState(false);

  const startEdit = () => {
    if (!doc.extraction) return;
    setEditFields(doc.extraction.fields.map((f) => ({ ...f })));
    setEditing(true);
  };

  const saveEdit = async () => {
    try {
      const res = await fetch(`${API}/api/documents/${doc.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fields: editFields }),
      });
      if (res.ok) {
        const updated = await res.json();
        onUpdate(updated);
      }
    } catch (err) {
      console.error("Save failed", err);
    }
    setEditing(false);
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const res = await fetch(`${API}/api/documents/${doc.id}/retry`, { method: "POST" });
      if (res.ok) {
        const updated = await res.json();
        onUpdate(updated);
      }
    } catch (err) {
      console.error("Retry failed", err);
    }
    setRetrying(false);
  };

  const handleDelete = async () => {
    try {
      const res = await fetch(`${API}/api/documents/${doc.id}`, { method: "DELETE" });
      if (res.ok) onDelete(doc.id);
    } catch (err) {
      console.error("Delete failed", err);
    }
  };

  const isPdf = doc.filename?.toLowerCase().endsWith(".pdf");
  const timeAgo = doc.uploaded_at
    ? new Date(doc.uploaded_at).toLocaleString()
    : "";

  return (
    <div className="document-card">
      {/* Header */}
      <div className="card-header">
        <div className="card-file-info">
          <div className="card-file-icon">{isPdf ? "📑" : "🖼️"}</div>
          <div style={{ minWidth: 0 }}>
            <div className="card-file-name" title={doc.filename}>{doc.filename}</div>
            <div className="card-file-time">{timeAgo}</div>
          </div>
        </div>
        <div className="card-actions">
          {doc.status === "completed" && (
            <button className="card-action-btn" onClick={startEdit} title="Edit">✏️</button>
          )}
          {doc.status === "failed" && (
            <button
              className="card-action-btn retry"
              onClick={handleRetry}
              disabled={retrying}
              title="Retry"
            >
              🔄
            </button>
          )}
          <button className="card-action-btn delete" onClick={handleDelete} title="Delete">🗑️</button>
        </div>
      </div>

      {/* Status */}
      <StatusBadge status={doc.status} />
      <ProgressBar status={doc.status} />

      {/* Processing skeleton */}
      {doc.status === "processing" && (
        <div style={{ marginTop: 16 }}>
          <div className="skeleton-line long" style={{ height: 14, background: "linear-gradient(90deg, var(--bg-secondary), rgba(148,163,184,0.08), var(--bg-secondary))", backgroundSize: "200% 100%", animation: "shimmer 2s infinite", borderRadius: 6, marginBottom: 10 }} />
          <div className="skeleton-line medium" style={{ width: "70%", height: 14, background: "linear-gradient(90deg, var(--bg-secondary), rgba(148,163,184,0.08), var(--bg-secondary))", backgroundSize: "200% 100%", animation: "shimmer 2s infinite", borderRadius: 6, marginBottom: 10 }} />
          <div className="skeleton-line short" style={{ width: "40%", height: 14, background: "linear-gradient(90deg, var(--bg-secondary), rgba(148,163,184,0.08), var(--bg-secondary))", backgroundSize: "200% 100%", animation: "shimmer 2s infinite", borderRadius: 6 }} />
        </div>
      )}

      {/* Error */}
      {doc.status === "failed" && doc.error && (
        <div className="error-message">⚠️ {doc.error}</div>
      )}

      {/* Extracted Data */}
      {doc.status === "completed" && doc.extraction && (
        <>
          <div className="doc-type-badge" style={{ marginTop: 14 }}>
            🏷️ {doc.extraction.document_type}
          </div>

          <div className="fields-list">
            {(editing ? editFields : doc.extraction.fields).map((field, i) => (
              <div className="field-item" key={i}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="field-label">{field.field_name}</div>
                  {editing ? (
                    <input
                      className="field-value-input"
                      value={editFields[i].value}
                      onChange={(e) => {
                        const updated = [...editFields];
                        updated[i] = { ...updated[i], value: e.target.value };
                        setEditFields(updated);
                      }}
                    />
                  ) : (
                    <div className="field-value">{field.value}</div>
                  )}
                </div>
                <ConfidenceBar confidence={field.confidence} />
              </div>
            ))}
          </div>
          

          {editing && (
            <div className="edit-actions">
              <button className="btn-cancel" onClick={() => setEditing(false)}>Cancel</button>
              <button className="btn-save" onClick={saveEdit}>💾 Save</button>
            </div>
          )}
        </>
      )}

      {/* Footer */}
      {doc.processing_time_ms != null && (
        <div className="card-footer">
          <span className="processing-time">⚡ {(doc.processing_time_ms / 1000).toFixed(2)}s</span>
          {doc.extraction && (
            <span className="processing-time">{doc.extraction.fields.length} fields extracted</span>
          )}
        </div>
      )}
    </div>
  );
}
