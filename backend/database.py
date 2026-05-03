"""
Async SQLite database layer for document storage and retrieval.
Uses aiosqlite for non-blocking database operations.
"""

from __future__ import annotations

import json
from typing import Optional

import aiosqlite

from config import DATABASE_PATH
from models import DocumentRecord, DocumentExtraction


async def init_db() -> None:
    """Create the documents table if it does not exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                uploaded_at TEXT NOT NULL,
                extraction_json TEXT,
                error TEXT,
                processing_time_ms INTEGER
            )
        """)
        await db.commit()


async def create_document(doc_id: str, filename: str, uploaded_at: str) -> DocumentRecord:
    """Insert a new document record."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO documents (id, filename, status, uploaded_at) VALUES (?, ?, 'pending', ?)",
            (doc_id, filename, uploaded_at),
        )
        await db.commit()
    return DocumentRecord(
        id=doc_id,
        filename=filename,
        status="pending",
        uploaded_at=uploaded_at,
    )


async def update_document_status(
    doc_id: str,
    status: str,
    extraction: Optional[DocumentExtraction] = None,
    error: Optional[str] = None,
    processing_time_ms: Optional[int] = None,
) -> None:
    """Update the status and result of a document."""
    extraction_json = extraction.model_dump_json() if extraction else None
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE documents
               SET status = ?, extraction_json = ?, error = ?, processing_time_ms = ?
               WHERE id = ?""",
            (status, extraction_json, error, processing_time_ms, doc_id),
        )
        await db.commit()


async def update_document_fields(doc_id: str, extraction: DocumentExtraction) -> None:
    """Update the extracted fields for a document (edit feature)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE documents SET extraction_json = ? WHERE id = ?",
            (extraction.model_dump_json(), doc_id),
        )
        await db.commit()


async def get_document(doc_id: str) -> Optional[DocumentRecord]:
    """Retrieve a single document by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_record(row)


async def get_all_documents() -> list[DocumentRecord]:
    """Retrieve all documents, ordered by upload time descending."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_record(r) for r in rows]


async def delete_document(doc_id: str) -> bool:
    """Delete a document record. Returns True if a row was deleted."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_stats() -> dict:
    """Compute processing statistics."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents")
        total = (await cursor.fetchone())["cnt"]

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE status = 'completed'")
        completed = (await cursor.fetchone())["cnt"]

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE status = 'failed'")
        failed = (await cursor.fetchone())["cnt"]

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE status = 'pending'")
        pending = (await cursor.fetchone())["cnt"]

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE status = 'processing'")
        processing = (await cursor.fetchone())["cnt"]

        cursor = await db.execute(
            "SELECT AVG(processing_time_ms) as avg_time FROM documents WHERE status = 'completed' AND processing_time_ms IS NOT NULL"
        )
        avg_row = await cursor.fetchone()
        avg_time = avg_row["avg_time"] if avg_row else None

        success_rate = (completed / total * 100) if total > 0 else None

    return {
        "total_documents": total,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "processing": processing,
        "average_processing_time_ms": round(avg_time, 1) if avg_time else None,
        "success_rate": round(success_rate, 1) if success_rate else None,
    }


def _row_to_record(row) -> DocumentRecord:
    """Convert a database row to a DocumentRecord."""
    extraction = None
    if row["extraction_json"]:
        extraction = DocumentExtraction.model_validate_json(row["extraction_json"])
    return DocumentRecord(
        id=row["id"],
        filename=row["filename"],
        status=row["status"],
        uploaded_at=row["uploaded_at"],
        extraction=extraction,
        error=row["error"],
        processing_time_ms=row["processing_time_ms"],
    )
