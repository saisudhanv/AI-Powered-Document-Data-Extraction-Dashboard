"""
File validation and preprocessing module.
Handles file type checking, size validation, and PDF-to-image conversion.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from PIL import Image

from config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES


class FileValidationError(Exception):
    """Raised when a file fails validation."""
    pass


def validate_file(filename: str, file_size: int) -> None:
    """
    Validate file extension and size.
    Raises FileValidationError if validation fails.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise FileValidationError(
            f"File too large ({file_size / (1024*1024):.1f} MB). Maximum: {max_mb:.0f} MB"
        )


def is_pdf(filename: str) -> bool:
    """Check if a file is a PDF based on extension."""
    return Path(filename).suffix.lower() == ".pdf"


def convert_pdf_to_images(pdf_bytes: bytes) -> list[bytes]:
    """
    Convert a PDF file to a list of PNG image byte arrays.
    Uses PyMuPDF (fitz) — no external system dependencies required.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise FileValidationError(
            "PDF processing requires 'pymupdf'. Install it: pip install pymupdf"
        )

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        result = []
        for page in doc:
            # Render at 200 DPI (default is 72, so scale factor ≈ 2.78)
            mat = fitz.Matrix(200 / 72, 200 / 72)
            pix = page.get_pixmap(matrix=mat)
            result.append(pix.tobytes("png"))
        doc.close()
        return result
    except Exception as e:
        raise FileValidationError(f"Failed to convert PDF: {str(e)}")


def optimize_image(image_bytes: bytes, max_dimension: int = 1600) -> bytes:
    """
    Resize image if larger than max_dimension to reduce token usage.
    Returns optimized image as PNG bytes.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert RGBA to RGB if needed
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background

        # Resize if too large
        w, h = img.size
        if max(w, h) > max_dimension:
            ratio = max_dimension / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception:
        # If optimization fails, return original bytes
        return image_bytes
