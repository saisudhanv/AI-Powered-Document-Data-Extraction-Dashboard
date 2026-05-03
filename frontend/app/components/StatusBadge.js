"use client";
export default function StatusBadge({ status }) {
  const labels = { pending: "Pending", processing: "Processing", completed: "Completed", failed: "Failed" };
  return (
    <span className={`status-badge ${status}`}>
      <span className={`status-dot ${status}`} />
      {labels[status] || status}
    </span>
  );
}
