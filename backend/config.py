"""
Configuration module for the Document Extraction Backend.
Loads environment variables and provides app-wide settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR.mkdir(exist_ok=True)
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "documents.db")))

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)

# --- File Upload Constraints ---
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".webp", ".bmp", ".tiff"}
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/bmp",
    "image/tiff",
    "application/pdf",
}

# --- Processing ---
MAX_CONCURRENT_EXTRACTIONS = 5
GEMINI_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds

# --- Server ---
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
