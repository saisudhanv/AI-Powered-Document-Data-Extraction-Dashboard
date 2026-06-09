"""
Pydantic models for the Document Extraction system.
These schemas define the data contracts for API requests/responses
and for enforcing structured output from the Gemini AI model.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Gemini Structured Output Schemas
# ---------------------------------------------------------------------------

class ExtractedField(BaseModel):
    """A single extracted field from a document."""
    field_name: str = Field(description="Name of the extracted field, e.g. 'Full Name', 'Date of Birth'")
    value: str = Field(description="The extracted value for this field")
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0 indicating how certain the extraction is",
        ge=0.0,
        le=1.0,
    )


class DocumentExtraction(BaseModel):
    """Complete extraction result for a single document."""
    document_type: str = Field(
        description="Type of document identified, e.g. 'Aadhaar Card', 'PAN Card', 'Passport', 'Driver License'"
    )
    fields: list[ExtractedField] = Field(
        description="List of all extracted fields from the document"
    )


# ---------------------------------------------------------------------------
# API Response Schemas
# ---------------------------------------------------------------------------

class DocumentRecord(BaseModel):
    """Represents a document record in the system."""
    id: str
    filename: str
    status: str  # "pending" | "processing" | "completed" | "failed"
    uploaded_at: str
    extraction: Optional[DocumentExtraction] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None
    user_id: Optional[str] = None


class UploadResponse(BaseModel):
    """Response returned after uploading documents."""
    message: str
    documents: list[DocumentRecord]


class StatsResponse(BaseModel):
    """Processing statistics."""
    total_documents: int
    completed: int
    failed: int
    pending: int
    processing: int
    average_processing_time_ms: Optional[float] = None
    success_rate: Optional[float] = None


class UpdateFieldsRequest(BaseModel):
    """Request body for editing extracted fields."""
    fields: list[ExtractedField]
