"""
FastAPI application — main entry point for the Document Extraction Backend.

Endpoints:
    POST   /api/upload              Upload single or multiple documents
    GET    /api/documents           List all documents with status & results
    GET    /api/documents/{id}      Get a single document
    PUT    /api/documents/{id}      Update extracted fields (edit feature)
    POST   /api/documents/{id}/retry  Retry a failed extraction
    DELETE /api/documents/{id}      Delete a document
    GET    /api/stats               Processing statistics
    GET    /api/status              SSE stream for real-time status updates
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import config
import database as db
from models import (
    DocumentRecord,
    DocumentExtraction,
    ExtractedField,
    UploadResponse,
    StatsResponse,
    UpdateFieldsRequest,
)
from file_handler import validate_file, is_pdf, convert_pdf_to_images, optimize_image, FileValidationError
from extraction import extract_document_data

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DocExtract AI",
    description="AI-Powered Document Data Extraction API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Semaphore to limit concurrent Gemini API calls
extraction_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_EXTRACTIONS)

# SSE subscribers for real-time updates (queue, user_id)
sse_subscribers: list[tuple[asyncio.Queue, str]] = []


@app.on_event("startup")
async def startup():
    """Initialize the database on startup."""
    await db.init_db()


# ---------------------------------------------------------------------------
# User Authentication / Dependency
# ---------------------------------------------------------------------------

async def get_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None)
) -> str:
    """Extract and validate the user ID from headers or query parameters."""
    uid = x_user_id or user_id
    if not uid:
        raise HTTPException(status_code=400, detail="X-User-ID header or user_id query parameter is required")
    return uid


# ---------------------------------------------------------------------------
# SSE Helpers
# ---------------------------------------------------------------------------

async def broadcast_update(doc: DocumentRecord) -> None:
    """Send a status update to all SSE subscribers of this user."""
    user_id = doc.user_id
    if not user_id:
        return
    data = doc.model_dump_json()
    dead_queues = []
    for q, sub_user_id in sse_subscribers:
        if sub_user_id == user_id:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                dead_queues.append((q, sub_user_id))
    for item in dead_queues:
        if item in sse_subscribers:
            sse_subscribers.remove(item)


# ---------------------------------------------------------------------------
# Background Processing
# ---------------------------------------------------------------------------

async def process_document(doc_id: str, file_path: Path, filename: str) -> None:
    """Process a single document: extract data using Gemini AI."""
    async with extraction_semaphore:
        # Update status to processing
        await db.update_document_status(doc_id, "processing")
        processing_doc = await db.get_document(doc_id)
        if processing_doc:
            await broadcast_update(processing_doc)

        start_time = time.time()
        try:
            # Read the file
            raw_bytes = file_path.read_bytes()

            # Convert PDF pages to images, or use image directly
            if is_pdf(filename):
                image_list = convert_pdf_to_images(raw_bytes)
            else:
                image_list = [raw_bytes]

            # Optimize images to reduce token usage
            image_list = [optimize_image(img) for img in image_list]

            # Call Gemini AI for extraction
            extraction = await extract_document_data(image_list)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Update with results
            await db.update_document_status(
                doc_id,
                "completed",
                extraction=extraction,
                processing_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            await db.update_document_status(
                doc_id,
                "failed",
                error=str(e),
                processing_time_ms=elapsed_ms,
            )

        # Broadcast final status
        updated_doc = await db.get_document(doc_id)
        if updated_doc:
            await broadcast_update(updated_doc)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    user_id: str = Depends(get_user_id)
):
    """
    Upload one or more documents for AI extraction.
    Supports images (PNG, JPG, JPEG, WebP, BMP, TIFF) and PDFs.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    documents: list[DocumentRecord] = []
    tasks: list[tuple[str, Path, str]] = []

    for file in files:
        # Read file content
        content = await file.read()

        # Validate
        try:
            validate_file(file.filename or "unknown", len(content))
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Generate ID and save file
        doc_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).isoformat()
        safe_name = f"{doc_id}_{file.filename}"
        file_path = config.UPLOAD_DIR / safe_name
        file_path.write_bytes(content)

        # Create database record
        doc = await db.create_document(doc_id, file.filename or "unknown", timestamp, user_id)
        documents.append(doc)
        tasks.append((doc_id, file_path, file.filename or "unknown"))

    # Kick off background extraction for each document
    for doc_id, file_path, filename in tasks:
        asyncio.create_task(process_document(doc_id, file_path, filename))

    return UploadResponse(
        message=f"Successfully uploaded {len(documents)} document(s). Processing started.",
        documents=documents,
    )


@app.get("/api/documents", response_model=list[DocumentRecord])
async def list_documents(user_id: str = Depends(get_user_id)):
    """List all uploaded documents with their extraction status and results."""
    return await db.get_all_documents(user_id)


@app.get("/api/documents/{doc_id}", response_model=DocumentRecord)
async def get_document(doc_id: str, user_id: str = Depends(get_user_id)):
    """Get details of a specific document."""
    doc = await db.get_document(doc_id)
    if not doc or doc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.put("/api/documents/{doc_id}", response_model=DocumentRecord)
async def update_document(doc_id: str, body: UpdateFieldsRequest, user_id: str = Depends(get_user_id)):
    """Update extracted fields for a document (edit feature)."""
    doc = await db.get_document(doc_id)
    if not doc or doc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document has no extraction data to edit")

    updated_extraction = DocumentExtraction(
        document_type=doc.extraction.document_type,
        fields=body.fields,
    )
    await db.update_document_fields(doc_id, updated_extraction)
    updated_doc = await db.get_document(doc_id)
    return updated_doc


@app.post("/api/documents/{doc_id}/retry", response_model=DocumentRecord)
async def retry_extraction(doc_id: str, user_id: str = Depends(get_user_id)):
    """Retry extraction for a failed document."""
    doc = await db.get_document(doc_id)
    if not doc or doc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status not in ("failed",):
        raise HTTPException(status_code=400, detail="Can only retry failed documents")

    # Reset status
    await db.update_document_status(doc_id, "pending")
    pending_doc = await db.get_document(doc_id)
    if pending_doc:
        await broadcast_update(pending_doc)

    # Find the file on disk
    matching_files = list(config.UPLOAD_DIR.glob(f"{doc_id}_*"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Original file not found on disk")

    file_path = matching_files[0]
    asyncio.create_task(process_document(doc_id, file_path, doc.filename))

    return await db.get_document(doc_id)


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, user_id: str = Depends(get_user_id)):
    """Delete a document and its file."""
    deleted = await db.delete_document(doc_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    # Clean up file
    for f in config.UPLOAD_DIR.glob(f"{doc_id}_*"):
        f.unlink(missing_ok=True)

    return {"message": "Document deleted"}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(user_id: str = Depends(get_user_id)):
    """Get processing statistics and performance metrics."""
    stats = await db.get_stats(user_id)
    return StatsResponse(**stats)


@app.get("/api/status")
async def status_stream(user_id: str = Depends(get_user_id)):
    """
    Server-Sent Events stream for real-time processing updates.
    Clients receive document status changes as they happen.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    sse_subscribers.append((queue, user_id))

    async def event_generator():
        try:
            # Send initial heartbeat
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            # Clean up subscriber
            for item in list(sse_subscribers):
                if item[0] is queue:
                    sse_subscribers.remove(item)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "DocExtract AI Backend"}
