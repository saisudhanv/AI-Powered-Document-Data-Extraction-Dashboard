"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import Header from "./components/Header";
import FileUpload from "./components/FileUpload";
import DocumentCard from "./components/DocumentCard";
import DataTable from "./components/DataTable";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const defaultStats = {
  total_documents: 0, completed: 0, failed: 0, pending: 0, processing: 0,
  average_processing_time_ms: null, success_rate: null,
};

export default function Home() {
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState(defaultStats);
  const [uploading, setUploading] = useState(false);
  const [view, setView] = useState("cards"); // "cards" | "table"
  const sseRef = useRef(null);

  // Fetch all documents
  const fetchDocs = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/documents`);
      if (res.ok) setDocuments(await res.json());
    } catch (e) { /* backend may not be running yet */ }
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/stats`);
      if (res.ok) setStats(await res.json());
    } catch (e) { /* ignore */ }
  }, []);

  // SSE connection for real-time updates
  useEffect(() => {
    fetchDocs();
    fetchStats();

    const connectSSE = () => {
      const es = new EventSource(`${API}/api/status`);
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "connected" || data.type === "heartbeat") return;
          // data is a DocumentRecord — update local state
          setDocuments((prev) => {
            const idx = prev.findIndex((d) => d.id === data.id);
            if (idx >= 0) {
              const updated = [...prev];
              updated[idx] = data;
              return updated;
            }
            return [data, ...prev];
          });
          fetchStats();
        } catch (e) { /* ignore parse errors */ }
      };
      es.onerror = () => {
        es.close();
        setTimeout(connectSSE, 3000); // reconnect
      };
      sseRef.current = es;
    };

    connectSSE();
    return () => sseRef.current?.close();
  }, [fetchDocs, fetchStats]);

  // Upload handler
  const handleUpload = async (files) => {
    setUploading(true);
    try {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      const res = await fetch(`${API}/api/upload`, { method: "POST", body: formData });
      if (res.ok) {
        const data = await res.json();
        setDocuments((prev) => [...data.documents, ...prev]);
        fetchStats();
      }
    } catch (err) {
      console.error("Upload failed", err);
    }
    setUploading(false);
  };

  // Update a document in local state
  const handleDocUpdate = (updated) => {
    setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    fetchStats();
  };

  // Remove a document from local state
  const handleDocDelete = (id) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    fetchStats();
  };

  return (
    <div className="app-container">
      <Header stats={stats} />
      <FileUpload onUpload={handleUpload} uploading={uploading} />

      {/* Results Section */}
      <div className="results-section">
        <div className="results-header">
          <h2 className="section-title">
            <span className="icon">📋</span> Extracted Documents
            <span className="results-count">({documents.length})</span>
          </h2>
          <div className="view-toggle">
            <button
              className={`view-toggle-btn ${view === "cards" ? "active" : ""}`}
              onClick={() => setView("cards")}
            >
              🃏 Cards
            </button>
            <button
              className={`view-toggle-btn ${view === "table" ? "active" : ""}`}
              onClick={() => setView("table")}
            >
              📊 Table
            </button>
          </div>
        </div>

        {documents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📂</div>
            <p className="empty-state-text">No documents yet</p>
            <p className="empty-state-hint">
              Upload Aadhaar, PAN, Passport or any official document to get started
            </p>
          </div>
        ) : view === "cards" ? (
          <div className="documents-grid">
            {documents.map((doc) => (
              <DocumentCard
                key={doc.id}
                doc={doc}
                onUpdate={handleDocUpdate}
                onDelete={handleDocDelete}
              />
            ))}
          </div>
        ) : (
          <DataTable documents={documents} />
        )}
      </div>
    </div>
  );
}
