# DocExtract AI — AI-Powered Document Data Extraction Dashboard

A full-stack application that uses **Google Gemini 2.5 Flash** to automatically extract structured data from official documents (Aadhaar Card, PAN Card, Passport, etc.). Upload documents, get instant AI-powered extraction with confidence scores, and manage results through a premium dashboard interface.


---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-File Upload** | Drag & drop or browse - upload multiple images/PDFs at once |
| **AI-Based Extraction** | Google Gemini 2.5 Flash extracts structured data from any official document |
| **Auto Document Detection** | AI identifies document type automatically (Aadhaar, PAN, Passport, etc.) |
| **Confidence Scores** | Per-field confidence indicators (color-coded bars) |
| **Editable Fields** | Inline editing of extracted data |
| **Retry Mechanism** | One-click retry for failed extractions with exponential backoff |
| **Real-Time Updates** | Server-Sent Events (SSE) for live processing status |
| **Performance Tracking** | Dashboard stats - avg processing time, success rate |
| **Dual View** | Card view and table view for extracted data |
| **Premium Dark UI** | Glassmorphism design with micro-animations |

---

## Setup Steps

### Prerequisites
- **Node.js** 18+ and npm
- **Python** 3.10+
- **Google Gemini API Key** (free at https://aistudio.google.com/apikey)
- **Poppler** (optional, for PDF support): [Windows releases](https://github.com/oschwartz10612/poppler-windows/releases)

### 1. Clone the Repository
```bash
git clone "https://github.com/saisudhanv/AI-Powered-Document-Data-Extraction-Dashboard.git"
cd Assignment
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure API key
copy .env.example .env
# Edit .env and set your GEMINI_API_KEY

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Access the Dashboard
Open **http://localhost:3000** in your browser.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 14)                 │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │  File Upload │ │ Document     │ │ Data Table       │  │
│  │  (Drag&Drop) │ │ Cards        │ │ (All Fields)     │  │
│  └──────┬───────┘ └──────────────┘ └──────────────────┘  │
│         │              ▲ SSE                              │
└─────────┼──────────────┼─────────────────────────────────┘
          │ POST /upload │ GET /documents
          ▼              │
┌─────────────────────────────────────────────────────────┐
│                 Backend (Python FastAPI)                  │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ File     │  │ Async Task   │  │ SQLite Database   │   │
│  │ Validator│──│ Queue (5     │──│ (documents table) │   │
│  │          │  │ concurrent)  │  │                   │   │
│  └──────────┘  └──────┬───────┘  └──────────────────┘   │
│                       │                                  │
└───────────────────────┼──────────────────────────────────┘
                        │ API Call
                        ▼
              ┌─────────────────────┐
              │ Google Gemini 2.5   │
              │ Flash (Multimodal)  │
              │ Structured Output   │
              └─────────────────────┘
```

### Request Flow
1. **Upload**: User drops documents → Frontend sends `POST /api/upload`
2. **Queue**: Backend validates files, saves to disk, creates DB records, kicks off async tasks
3. **Process**: Worker sends image(s) to Gemini with structured output schema
4. **Stream**: Results broadcast via SSE → Frontend updates in real-time
5. **Display**: Extracted data shown in cards/table with confidence scores

---

## AI Approach

### Why Google Gemini 2.5 Flash?

| Criteria | Gemini 2.5 Flash | OpenAI GPT-4o | Tesseract OCR |
|----------|-----------------|---------------|---------------|
| Native Vision | Direct image(Yes) | Direct image(Yes) | Text only(No) |
| Structured Output | Pydantic schema(Yes) | JSON mode(Yes) | Raw text(No) |
| Cost (per 1M tokens) | ~$0.15 input | ~$2.50 input | Free |
| Generic Doc Handling | Prompt-driven(Yes) | Prompt-driven(Yes) | Needs rules(No) |
| Free Tier | Generous(Yes) | Paid only(No) | Free(Yes) |

### How It Works

1. **Image Input**: Documents are sent as images directly to Gemini's multimodal endpoint
2. **Generic Prompt**: A carefully crafted prompt instructs the AI to:
   - Identify document type dynamically (not hardcoded)
   - Extract ALL visible fields
   - Provide confidence scores (0.0–1.0) per field
3. **Structured Output**: Pydantic schema enforces JSON structure - no regex parsing needed
4. **Retry Logic**: 3 attempts with exponential backoff on failure

### Trade-offs
- **Pros**: Extremely accurate, handles diverse layouts, no preprocessing needed, very cheap
- **Cons**: Requires network access, API key needed, slight latency (~3-5s per doc)
- **Alternative**: For offline use, combine Tesseract + local LLM - but accuracy drops significantly

---

## Scaling Strategy

### Current Design (Assignment Scope)
- **5 concurrent** Gemini API calls via `asyncio.Semaphore`
- **Throughput**: ~50 docs in ~50 seconds (10 batches × 5s avg response)
- **Well within** the 30-minute requirement

### Production Scaling Path

| Scale | Approach | Throughput |
|-------|----------|-----------|
| Current | Single FastAPI + asyncio (5 workers) | ~50 docs/min |
| Medium | Celery + Redis + 10 workers | ~200 docs/min |
| Large | Kubernetes + auto-scaling + Batch API | 1000+ docs/min |

**Key strategies:**
1. **Celery + Redis** - task queue for worker decoupling
2. **Gemini Batch API** - 50% cost reduction for non-real-time jobs
3. **Horizontal scaling** - add worker pods independently of API servers
4. **Image preprocessing** - resize/compress to reduce token count
5. **Deduplication** - hash-based caching to avoid re-processing identical docs

---

## Cost Estimation

### Gemini 2.5 Flash Pricing

| Metric | Cost |
|--------|------|
| Input tokens (≤200K) | $0.15 / 1M tokens |
| Output tokens | $0.60 / 1M tokens |
| Image input | ~258 tokens/image |

### Per-Document Cost

| Component | Tokens | Cost |
|-----------|--------|------|
| Image (1 page) | ~258 | $0.000039 |
| Prompt text | ~200 | $0.000030 |
| Output JSON | ~300 | $0.000180 |
| **Total** | **~758** | **~$0.00025** |

### Volume Estimates

| Volume | Standard | Batch API (50% off) |
|--------|----------|---------------------|
| 50 docs | ~$0.012 | ~$0.006 |
| 1,000 docs | ~$0.25 | ~$0.125 |
| 10,000 docs | ~$2.50 | ~$1.25 |

### Optimization Strategies
- **Free Tier**: Sufficient for development & small-scale testing
- **Batch API**: 50% discount for async processing
- **Caching**: Skip duplicate documents via file hash
- **Model Selection**: Use `gemini-2.5-flash-lite` for simpler documents
- **Image Optimization**: Resize to 1600px max dimension before sending

> **Bottom line**: Processing 50 documents costs less than $0.02 - effectively free.

---


## Project Structure

```
Assignment/
├── backend/
│   ├── main.py              # FastAPI app & API routes
│   ├── extraction.py         # Gemini AI extraction logic
│   ├── models.py             # Pydantic schemas
│   ├── database.py           # SQLite async operations
│   ├── file_handler.py       # File validation & PDF conversion
│   ├── config.py             # Environment configuration
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment template
│   └── uploads/              # Uploaded files storage
│
├── frontend/
│   ├── app/
│   │   ├── layout.js         # Root layout with SEO metadata
│   │   ├── page.js           # Main dashboard page
│   │   ├── globals.css       # Design system (dark glassmorphism)
│   │   └── components/
│   │       ├── Header.js     # Branding + live stats
│   │       ├── FileUpload.js # Drag & drop multi-upload
│   │       ├── DocumentCard.js # Result card with edit/retry
│   │       ├── DataTable.js  # Table view of all fields
│   │       ├── ConfidenceBar.js # Confidence score visualizer
│   │       ├── ProgressBar.js   # Processing progress
│   │       └── StatusBadge.js   # Status indicator
│   ├── package.json
│   └── next.config.js
│
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload documents for extraction |
| `GET` | `/api/documents` | List all documents with results |
| `GET` | `/api/documents/{id}` | Get single document details |
| `PUT` | `/api/documents/{id}` | Edit extracted fields |
| `POST` | `/api/documents/{id}/retry` | Retry failed extraction |
| `DELETE` | `/api/documents/{id}` | Delete a document |
| `GET` | `/api/stats` | Processing statistics |
| `GET` | `/api/status` | SSE stream for real-time updates |
| `GET` | `/api/health` | Health check |

---

