"use client";
export default function ProgressBar({ status }) {
  if (status !== "processing") return null;
  return (
    <div className="progress-bar-track">
      <div className="progress-bar-fill indeterminate" />
    </div>
  );
}
