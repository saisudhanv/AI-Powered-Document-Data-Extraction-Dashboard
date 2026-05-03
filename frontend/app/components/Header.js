"use client";

export default function Header({ stats }) {
  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">📄</div>
        <div>
          <h1 className="header-title">DocExtract AI</h1>
          <p className="header-subtitle">AI-Powered Document Data Extraction</p>
        </div>
      </div>
      <div className="header-stats">
        <div className="stat-item">
          <div className="stat-value">{stats.total_documents}</div>
          <div className="stat-label">Total</div>
        </div>
        <div className="stat-item">
          <div className="stat-value" style={{ color: "var(--accent-emerald)" }}>
            {stats.completed}
          </div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat-item">
          <div className="stat-value" style={{ color: "var(--accent-red)" }}>
            {stats.failed}
          </div>
          <div className="stat-label">Failed</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">
            {stats.average_processing_time_ms
              ? `${(stats.average_processing_time_ms / 1000).toFixed(1)}s`
              : "—"}
          </div>
          <div className="stat-label">Avg Time</div>
        </div>
      </div>
    </header>
  );
}
