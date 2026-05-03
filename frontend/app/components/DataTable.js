"use client";
import StatusBadge from "./StatusBadge";
import ConfidenceBar from "./ConfidenceBar";

export default function DataTable({ documents }) {
  // Flatten all documents into rows
  const rows = [];
  documents.forEach((doc) => {
    if (doc.extraction) {
      doc.extraction.fields.forEach((field) => {
        rows.push({ doc, field });
      });
    }
  });

  if (rows.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "40px 24px" }}>
        <p className="empty-state-text">No extracted data to display in table view</p>
      </div>
    );
  }

  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Document</th>
            <th>Type</th>
            <th>Field</th>
            <th>Value</th>
            <th>Confidence</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td style={{ fontWeight: 500, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {row.doc.filename}
              </td>
              <td>
                <span className="doc-type-badge" style={{ margin: 0 }}>
                  {row.doc.extraction.document_type}
                </span>
              </td>
              <td style={{ color: "var(--text-muted)", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                {row.field.field_name}
              </td>
              <td style={{ fontWeight: 500 }}>{row.field.value}</td>
              <td style={{ minWidth: 120 }}>
                <ConfidenceBar confidence={row.field.confidence} />
              </td>
              <td>
                <StatusBadge status={row.doc.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
