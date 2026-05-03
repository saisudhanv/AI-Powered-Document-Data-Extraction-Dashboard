"""
AI-based document data extraction using Google Gemini.
Sends document images to Gemini 2.5 Flash and receives structured JSON output.
"""

from __future__ import annotations

import asyncio
import base64
import time
import traceback
from typing import Optional

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_RETRIES, RETRY_BACKOFF_BASE
from models import DocumentExtraction, ExtractedField


# ---------------------------------------------------------------------------
# Extraction Prompt — Generic, not hardcoded for any specific document type
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are an expert document analysis AI. Analyze the provided official document image and extract ALL relevant information.

INSTRUCTIONS:
1. **Identify the document type** — Determine what kind of document this is (e.g., Aadhaar Card, PAN Card, Passport, Driver's License, Voter ID Card, Birth Certificate, or any other official/government document). If you cannot determine the exact type, use a descriptive name like "Official ID Card" or "Government Document".

2. **Extract every visible field** — Look for and extract ALL text fields visible on the document. Common fields include (but are NOT limited to):
   - Full Name / Name
   - Date of Birth / DOB
   - Address (full address if available)
   - ID Number / Document Number / Card Number
   - Gender / Sex
   - Father's Name / Mother's Name / Spouse's Name
   - Issue Date / Date of Issue
   - Expiry Date / Valid Until
   - Place of Birth / Place of Issue
   - Nationality
   - Blood Group
   - Any other visible fields

3. **Confidence scoring** — For each extracted field, provide a confidence score:
   - 1.0 = Clearly readable, high certainty
   - 0.7-0.9 = Mostly readable, minor uncertainty
   - 0.4-0.6 = Partially readable, some guessing involved
   - 0.1-0.3 = Barely readable, low confidence
   - Do NOT include fields you cannot read at all

4. **Format guidelines**:
   - Use standardized field names (e.g., "Full Name" not "nm" or "NAME")
   - Dates should be in DD/MM/YYYY or DD-MM-YYYY format where possible
   - Preserve the original language of the values but use English field names
   - For addresses, combine multi-line addresses into a single value

Return the extraction in the exact JSON schema provided."""


def _get_client() -> genai.Client:
    """Create and return a Gemini client."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get a free API key at https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=GEMINI_API_KEY)


async def extract_document_data(image_bytes_list: list[bytes]) -> DocumentExtraction:
    """
    Extract structured data from document image(s) using Gemini.
    
    Args:
        image_bytes_list: List of image byte arrays (one per page).
                          For single-page docs, this will be a list with one element.
    
    Returns:
        DocumentExtraction with document type, fields, and confidence scores.
    
    Raises:
        Exception if extraction fails after all retries.
    """
    client = _get_client()
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Build content parts: images + prompt
            content_parts = []
            for img_bytes in image_bytes_list:
                b64_data = base64.b64encode(img_bytes).decode("utf-8")
                content_parts.append(
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                )

            content_parts.append(EXTRACTION_PROMPT)

            # Call Gemini with structured output
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=GEMINI_MODEL,
                contents=content_parts,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DocumentExtraction,
                    temperature=0.1,  # Low temperature for deterministic extraction
                ),
            )

            # Parse and validate the structured response
            result = DocumentExtraction.model_validate_json(response.text)

            # Sanity check: ensure we got at least one field
            if not result.fields:
                raise ValueError("No fields were extracted from the document")

            return result

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_BASE ** attempt
                await asyncio.sleep(wait_time)
            else:
                break

    raise RuntimeError(
        f"Extraction failed after {MAX_RETRIES} attempts. Last error: {str(last_error)}"
    )
