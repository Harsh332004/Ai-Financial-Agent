import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import agent, alerts, auth, companies, documents, reports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tag metadata — controls display order and descriptions in Swagger UI
# ---------------------------------------------------------------------------
tags_metadata = [
    {
        "name": "auth",
        "description": (
            "**Authentication** — Register a new account, obtain a JWT access token via login, "
            "and inspect the currently authenticated user. "
            "After logging in, copy the `access_token` and paste it into the 🔒 **Authorize** dialog above."
        ),
    },
    {
        "name": "companies",
        "description": (
            "**Companies** — Manage the companies you want to track. "
            "Each company has an optional stock ticker and exchange for live market data lookups."
        ),
    },
    {
        "name": "documents",
        "description": (
            "**Documents** — Upload financial documents (PDF, PNG, JPG, TIFF …). "
            "After upload the document is immediately returned with `status: processing`. "
            "OCR extraction, text chunking, and FAISS/BM25 indexing run in the background; "
            "the status transitions to `ready` (or `failed`) when complete."
        ),
    },
    {
        "name": "agent",
        "description": (
            "**AI Agent** — Run the ReAct financial analyst agent against a company's documents and live market data. "
            "Submitting a task returns a `run_id` immediately (HTTP 202). "
            "Poll `GET /agent/runs/{id}/status` until `status` is `done` or `failed`, "
            "then fetch the full reasoning trace via `GET /agent/runs/{id}`."
        ),
    },
    {
        "name": "reports",
        "description": (
            "**Reports** — List and download the PDF reports that the AI agent generates "
            "at the end of each analysis run."
        ),
    },
    {
        "name": "alerts",
        "description": (
            "**Alerts** — View risk alerts raised by the agent (e.g. revenue decline, high debt). "
            "Alerts can be filtered by company, severity level, or acknowledgement status, "
            "and acknowledged once reviewed."
        ),
    },
    {
        "name": "system",
        "description": "**System** — Health check and platform status endpoints.",
    },
]

app = FastAPI(
    title="AI Financial Operations Agent Platform",
    description=(
        "## AI-powered financial document analysis\n\n"
        "Upload PDF/image financial reports, run an AI agent that reads the documents, "
        "fetches live market data, calculates ratios, raises alerts, and generates a PDF report.\n\n"
        "### Quick-start\n"
        "1. `POST /auth/register` — create an account\n"
        "2. `POST /auth/login` — get a JWT token\n"
        "3. Click **Authorize 🔒** and paste the token\n"
        "4. `POST /companies` — add a company (e.g. Apple / AAPL)\n"
        "5. `POST /documents/upload` — upload a financial PDF\n"
        "6. `POST /agent/run` — start the AI analysis\n"
        "7. Poll `GET /agent/runs/{id}/status` until done\n"
        "8. Download the report via `GET /reports/{id}/download`\n"
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={"name": "AI Financial Agent", "url": "http://localhost:8000"},
    license_info={"name": "MIT"},
)

allowed_origins = list(
    {
        settings.FRONTEND_ORIGIN,
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        # Angular dev server
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/auth",      tags=["auth"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(agent.router,     prefix="/agent",     tags=["agent"])
app.include_router(reports.router,   prefix="/reports",   tags=["reports"])
app.include_router(alerts.router,    prefix="/alerts",    tags=["alerts"])


@app.get(
    "/health",
    tags=["system"],
    summary="Health check",
    description="Returns `{status: ok}` when the server is running. No authentication required.",
    response_description="Server is healthy",
)
async def health() -> dict:
    return {"status": "ok"}
