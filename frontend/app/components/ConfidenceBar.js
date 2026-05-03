"use client";
export default function ConfidenceBar({ confidence }) {
  const pct = Math.round(confidence * 100);
  const level = pct >= 80 ? "high" : pct >= 50 ? "medium" : "low";
  return (
    <div className="confidence-container">
      <div className="confidence-bar-track">
        <div className={`confidence-bar-fill ${level}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`confidence-label ${level}`}>{pct}%</span>
    </div>
  );
}
