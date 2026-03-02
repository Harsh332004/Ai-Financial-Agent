from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import AsyncSessionLocal, get_db
from backend.models.agent_run import AgentRun
from backend.models.company import Company
from backend.models.user import User
from backend.schemas.agent import AgentRunCreate, AgentRunDetailResponse, AgentRunResponse
from backend.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_agent_background(
    run_id: uuid.UUID, task: str, company_id: str, company_name: str, user_id: str,
) -> None:
    """Background task wrapper — creates its own DB session."""
    async with AsyncSessionLocal() as db:
        from backend.agent.orchestrator import FinancialAgent
        agent = FinancialAgent(
            run_id=run_id, db=db, company_id=company_id, user_id=user_id,
        )
        try:
            await agent.run(task=task, company_name=company_name)
        except Exception as e:
            logger.exception("Background agent run %s failed: %s", run_id, e)
            # Ensure the run is marked as failed even if the orchestrator didn't handle it
            try:
                from sqlalchemy import select
                from backend.models.agent_run import AgentRun
                result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
                run = result.scalar_one_or_none()
                if run and run.status == "running":
                    from datetime import datetime
                    run.status = "failed"
                    run.error_message = str(e)
                    run.finished_at = datetime.utcnow()
                    await db.commit()
            except Exception:
                logger.exception("Failed to mark run %s as failed", run_id)


@router.post(
    "/run",
    response_model=AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an AI agent analysis run",
    description=(
        "Submit a financial analysis task for the AI agent to execute against a company's documents.\n\n"
        "**Returns immediately (HTTP 202)** with a `run_id` — the agent runs in the background.\n\n"
        "**Agent capabilities:**\n"
        "- 📄 `rag_search` — searches uploaded documents with hybrid FAISS + BM25 retrieval\n"
        "- 📈 `fetch_market_data` — live stock price, P/E, margins, growth via yfinance\n"
        "- 📰 `fetch_news` — recent news via NewsAPI (yfinance fallback)\n"
        "- 🧮 `calculate_financial_ratios` — PE, D/E, ROE, margins with good/neutral/bad labels\n"
        "- 🚨 `create_alert` — saves risk alerts to the database\n"
        "- 📊 `generate_pdf_report` — creates a reportlab PDF saved to `reports/`\n\n"
        "**Example task:** `\"Analyze Apple's financial health and flag any significant risks.\"`\n\n"
        "Requires a valid `GROQ_API_KEY` in `.env`."
    ),
    response_description="Agent run record with status=running and a run_id to track progress",
)
async def start_agent_run(
    payload: AgentRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentRun:
    result = await db.execute(select(Company).where(Company.id == payload.company_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    run = AgentRun(
        user_id=current_user.id,
        company_id=payload.company_id,
        task=payload.task,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(
        _run_agent_background,
        run_id=run.id,
        task=payload.task,
        company_id=str(payload.company_id),
        company_name=company.name,
        user_id=str(current_user.id),
    )

    logger.info("Started agent run %s for company %s", run.id, company.name)
    return run


@router.get(
    "/runs",
    response_model=list[AgentRunResponse],
    summary="List your agent runs",
    description=(
        "Returns all agent runs submitted by the currently authenticated user, "
        "sorted by start time (newest first).\n\n"
        "Each run shows its `status`: `running` | `done` | `failed`."
    ),
    response_description="Array of agent run summaries",
)
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AgentRun]:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.user_id == current_user.id)
        .order_by(AgentRun.started_at.desc())
    )
    return list(result.scalars().all())


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunDetailResponse,
    summary="Get full agent run detail with reasoning trace",
    description=(
        "Retrieve the complete detail of an agent run, including:\n\n"
        "- `final_answer` — the agent's written analysis\n"
        "- `tool_calls` — every step the agent took: tool name, input, output, and duration\n"
        "- `status` — `running` | `done` | `failed`\n"
        "- `error_message` — present if status is `failed`\n\n"
        "The `tool_calls` list is the full **reasoning trace** — you can see exactly how the "
        "agent arrived at its conclusions."
    ),
    response_description="Full agent run with tool call trace",
)
async def get_run_detail(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentRun:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.id == run_id)
        .options(selectinload(AgentRun.tool_calls))
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return run


@router.get(
    "/runs/{run_id}/status",
    summary="Poll agent run status",
    description=(
        "Lightweight endpoint to check whether a run is still in progress.\n\n"
        "Returns `{run_id, status, finished_at}` — poll this every 2–3 seconds until "
        "`status` is `done` or `failed`, then call `GET /agent/runs/{id}` for the full result."
    ),
    response_description="Current run status",
)
async def get_run_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(AgentRun.id, AgentRun.status, AgentRun.finished_at)
        .where(AgentRun.id == run_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return {"run_id": str(row.id), "status": row.status, "finished_at": row.finished_at}
