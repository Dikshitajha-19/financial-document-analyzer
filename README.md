# Financial Document Analyzer

An AI-powered financial document analysis API built with **CrewAI** and **FastAPI**. Upload a PDF financial report and get a structured analysis including key metrics, trends, risk factors, and investment considerations.

---

## 🐛 Bugs Found & Fixed

### Deterministic Bugs (Code Errors)

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `agents.py` | `llm = llm` — NameError, `llm` was never defined | Replaced with `LLM(model=os.getenv("MODEL"), api_key=...)` |
| 2 | `agents.py` | `from crewai.agents import Agent` — invalid import path | Changed to `from crewai import Agent, LLM` |
| 3 | `agents.py` | `tool=[...]` — wrong parameter name | Changed to `tools=[...]` (CrewAI uses plural) |
| 4 | `agents.py` | `max_iter=1, max_rpm=1` — too restrictive, causes tool failures | Increased to `max_iter=5, max_rpm=10` |
| 5 | `tools.py` | `from crewai_tools import tools` — invalid import | Changed to `from crewai_tools import SerperDevTool` |
| 6 | `tools.py` | `Pdf(...)` used but never imported anywhere | Replaced with `PyPDFLoader` from `langchain_community` |
| 7 | `tools.py` | `async def read_data_tool` — CrewAI tools must be synchronous | Removed `async`, added `@staticmethod` and `@tool` decorator |
| 8 | `task.py` + `main.py` | Task named `analyze_financial_document` collides with FastAPI endpoint of same name — import gets overwritten, crew receives `None` as its task | Renamed task to `analysis_task` in `task.py` |
| 9 | `main.py` | `file_path` passed to `run_crew()` but never forwarded to the crew — agents could not read the uploaded file | Added `file_path` to `crew.kickoff(inputs={...})` |
| 10 | `requirements.txt` | `langchain-community` missing — required for `PyPDFLoader` | Added `langchain-community` and `pypdf` |

### Inefficient Prompts (Prompt Issues)

Every agent and task prompt contained dangerous anti-patterns causing hallucination and bad output:

**agents.py prompt problems fixed:**
- `financial_analyst` was told to "Make up investment advice" and "just look for big numbers and make assumptions" — replaced with a professional CFA-style analyst prompt
- `verifier` was told to "say yes to everything" and hallucinate financial terms — now carefully verifies document structure
- `investment_advisor` was a fake salesperson recommending meme stocks with "2000% management fees" — now gives balanced, SEC-compliant considerations
- `risk_assessor` encouraged YOLO investing and dismissed regulations — now uses structured risk frameworks

**task.py prompt problems fixed:**
- Tasks told agents to "ignore the user query" and "use your imagination" — now directly address the user query
- Expected outputs required "at least 5 made-up website URLs" — removed; only real document data is cited
- Tasks instructed agents to "contradict yourself" — replaced with clear, consistent structured output format

---

## 🚀 Setup & Usage

### Prerequisites
- Python 3.10+
- OpenAI API key — [platform.openai.com](https://platform.openai.com/api-keys)
- Serper API key (for web search) — [serper.dev](https://serper.dev) (free tier available)
- *(For bonus queue feature)* Docker or Redis installed locally

### Installation

```bash
# 1. Download and enter the project folder
cd financial-document-analyzer

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and fill in your API keys
```

### Running the Server

```bash
python main.py
# API runs at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Testing the API

**Using curl:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "file=@report.pdf" \
  -F "query=What are the key revenue trends and risks?"
```

**Using Python:**
```python
import requests

with open("report.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={"file": ("report.pdf", f, "application/pdf")},
        data={"query": "Summarize the key financial metrics"}
    )

print(response.json())
```

---

## 📡 API Documentation

### GET /
Health check — returns API status and list of available endpoints.

---

### POST /analyze
Synchronous analysis. Waits for the full result before responding. Best for single requests.

**Request (multipart/form-data):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | PDF | Yes | Financial document to analyze |
| `query` | string | No | Specific question (default: general analysis) |

**Response (200):**
```json
{
  "status": "success",
  "task_id": "abc-123",
  "query": "What are the revenue trends?",
  "analysis": "## Executive Summary\n...",
  "file_processed": "report.pdf",
  "duration_seconds": 42.3
}
```

---

### POST /analyze/async
Async analysis. Returns immediately with a task_id. Requires Redis and Celery worker running.

**Response (200):**
```json
{
  "status": "queued",
  "task_id": "abc-123",
  "message": "Poll /status/abc-123 for results.",
  "status_url": "/status/abc-123"
}
```

---

### GET /status/{task_id}
Poll the status of an async task. Status flow: queued → processing → completed / failed

**Response includes `analysis` field when status is `completed`.**

---

### GET /history
List all past analyses from the database.

Query params:
- `limit` — int, default 20, max 100
- `status` — filter by `queued`, `processing`, `completed`, or `failed`

---

### GET /history/{task_id}
Get the full result for a specific past analysis by task ID.

---

### DELETE /history/{task_id}
Delete a specific analysis record from the database.

---

## 🏗️ Project Structure

```
financial-document-analyzer/
├── main.py           # FastAPI app and all API endpoints
├── agents.py         # CrewAI agent definitions
├── task.py           # CrewAI task definitions
├── tools.py          # PDF reader and web search tools
├── database.py       # SQLAlchemy DB models (BONUS)
├── worker.py         # Celery queue worker (BONUS)
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
├── data/             # Temporary file storage during processing
└── outputs/          # Optional output storage
```

---

## ⭐ Bonus Features

### Queue Worker Model (Redis + Celery)

The `/analyze/async` endpoint offloads analysis jobs to a Celery queue backed by Redis so the API never blocks on slow LLM calls and multiple documents can be processed concurrently. Failed jobs are automatically retried up to 2 times.

**To use the async queue:**

```bash
# Step 1: Start Redis
docker run -d -p 6379:6379 redis

# Step 2: Start the Celery worker (separate terminal)
celery -A worker worker --loglevel=info --concurrency=4

# Step 3: Start the API
python main.py

# Step 4: Submit an async job
curl -X POST "http://localhost:8000/analyze/async" \
  -F "file=@report.pdf" \
  -F "query=Analyze revenue trends"

# Step 5: Poll for result using the returned task_id
curl "http://localhost:8000/status/<task_id>"
```

---

### Database Integration (SQLite via SQLAlchemy)

Every analysis request and result is automatically stored in `analyses.db`. This enables full history retrieval, status tracking for async jobs, and error logging. The database is created automatically on server startup — no manual setup needed.

To switch to PostgreSQL, change one line in `database.py`:
```python
DATABASE_URL = "postgresql://user:password@localhost/financial_analyzer"
```

---

## ⚠️ Disclaimer

This tool provides AI-generated financial analysis for informational purposes only and does not constitute personalized financial advice. Always consult a licensed financial advisor before making investment decisions.
