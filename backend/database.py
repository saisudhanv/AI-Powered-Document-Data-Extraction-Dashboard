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
    """Create the documents table if it does not exist and handle migrations."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                uploaded_at TEXT NOT NULL,
                extraction_json TEXT,
                error TEXT,
                processing_time_ms INTEGER,
                user_id TEXT
            )
        """)
        # Schema migration: Add user_id column if it doesn't exist in existing tables
        try:
            await db.execute("ALTER TABLE documents ADD COLUMN user_id TEXT")
        except Exception:
            pass  # Column already exists
        await db.commit()


async def create_document(doc_id: str, filename: str, uploaded_at: str, user_id: str) -> DocumentRecord:
    """Insert a new document record."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO documents (id, filename, status, uploaded_at, user_id) VALUES (?, ?, 'pending', ?, ?)",
            (doc_id, filename, uploaded_at, user_id),
        )
        await db.commit()
    return DocumentRecord(
        id=doc_id,
        filename=filename,
        status="pending",
        uploaded_at=uploaded_at,
        user_id=user_id,
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


async def get_all_documents(user_id: str) -> list[DocumentRecord]:
    """Retrieve all documents belonging to a user, ordered by upload time descending."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,)
        )
        rows = await cursor.fetchall()
        return [_row_to_record(r) for r in rows]


async def delete_document(doc_id: str, user_id: str) -> bool:
    """Delete a document record belonging to the user. Returns True if a row was deleted."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_stats(user_id: str) -> dict:
    """Compute processing statistics for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE user_id = ?", (user_id,))
        total = (await cursor.fetchone())["cnt"]

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE status = 'completed' AND user_id = ?", (user_id,))
        completed = (await cursor.fetchone())["cnt"]

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE status = 'failed' AND user_id = ?", (user_id,))
        failed = (await cursor.fetchone())["cnt"]

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE status = 'pending' AND user_id = ?", (user_id,))
        pending = (await cursor.fetchone())["cnt"]

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM documents WHERE status = 'processing' AND user_id = ?", (user_id,))
        processing = (await cursor.fetchone())["cnt"]

        cursor = await db.execute(
            "SELECT AVG(processing_time_ms) as avg_time FROM documents WHERE status = 'completed' AND processing_time_ms IS NOT NULL AND user_id = ?", (user_id,)
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
        "success_rate": round(success_rate, 1) if
         success_rate else None,
    }


def _row_to_record(row) -> DocumentRecord:
    """Convert a database row to a DocumentRecord."""
    extraction = None
    if row["extraction_json"]:
        extraction = DocumentExtraction.model_validate_json(row["extraction_json"])
    
    # Retrieve user_id, handle safely if migration hasn't populated it
    user_id = None
    try:
        user_id = row["user_id"]
    except (IndexError, KeyError):
        pass

    return DocumentRecord(
        id=row["id"],
        filename=row["filename"],
        status=row["status"],
        uploaded_at=row["uploaded_at"],
        extraction=extraction,
        error=row["error"],
        processing_time_ms=row["processing_time_ms"],
        user_id=user_id,
    )
