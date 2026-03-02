from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools.alert_tool import create_alert
from backend.agent.tools.calc_tool import calculate_financial_ratios
from backend.agent.tools.market_tool import fetch_market_data
from backend.agent.tools.news_tool import fetch_news
from backend.agent.tools.rag_tool import rag_search
from backend.agent.tools.report_tool import generate_pdf_report
from backend.config import settings
from backend.models.agent_run import AgentRun
from backend.models.report import Report
from backend.models.tool_call import ToolCall

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10

# ------------------------------------------------------------------
# Prompt cache — keeps system prompt + per-company context stable
# ------------------------------------------------------------------
_prompt_cache: dict[str, str | dict] = {}


# ------------------------------------------------------------------
# Tool definitions for Groq tool-calling API
# ------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": "Search uploaded financial documents for a company using semantic + keyword hybrid search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "company_id": {"type": "string", "description": "Company UUID string"},
                },
                "required": ["query", "company_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_market_data",
            "description": "Fetch live stock market data for a ticker (price, P/E, debt, margins, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL)"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_news",
            "description": "Fetch recent news articles about a company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "ticker": {"type": "string"},
                },
                "required": ["company_name", "ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_financial_ratios",
            "description": "Calculate and interpret financial ratios (PE, D/E, margins, growth etc.) from raw financial data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "Flat dict of raw financial data (compatible with yfinance info output)",
                    },
                },
                "required": ["data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_alert",
            "description": "Create a financial alert for significant findings (revenue decline, high debt, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_id": {"type": "string"},
                    "run_id": {"type": "string"},
                    "level": {"type": "string", "enum": ["info", "warning", "critical"]},
                    "message": {"type": "string"},
                    "details": {"type": "object"},
                },
                "required": ["company_id", "run_id", "level", "message", "details"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_pdf_report",
            "description": "Generate a PDF financial analysis report and save it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "object",
                        "description": (
                            "Report content dict with keys: summary (str), key_findings (list[str]), "
                            "market_data (dict), ratios (dict), alerts_summary (list[dict]), news_headlines (list[str])"
                        ),
                    },
                    "company_name": {"type": "string"},
                    "run_id": {"type": "string"},
                },
                "required": ["content", "company_name", "run_id"],
            },
        },
    },
]


class FinancialAgent:
    """ReAct agent that uses Groq tool-calling to analyze company financials."""

    def __init__(self, run_id: uuid.UUID, db: AsyncSession, company_id: str, user_id: str = ""):
        self.run_id = run_id
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
        self._report_generated = False
        self._collected_data: dict = {}

    async def run(self, task: str, company_name: str = "Unknown Company") -> str:
        """Execute the agent loop. Returns the final answer string."""
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)

        # ── Prompt caching ──────────────────────────────────────────────
        # Keep system prompt 100% identical every call → enables Groq's
        # built-in prompt prefix caching. Dynamic content goes in user msg.
        if "system_prompt" not in _prompt_cache:
            _prompt_cache["system_prompt"] = SYSTEM_PROMPT

        cached_system_prompt = _prompt_cache["system_prompt"]

        # CACHED (stays identical every call):
        system_msg = {"role": "system", "content": cached_system_prompt}

        # NOT CACHED (changes every call — dynamic context + question):
        user_msg = {
            "role": "user",
            "content": (
                f"Company: {company_name} (ID: {self.company_id})\n\n"
                f"Task: {task}"
            ),
        }

        messages = [system_msg, user_msg]

        try:
            for step in range(MAX_ITERATIONS):
                logger.info("Agent step %d (run=%s)", step + 1, self.run_id)
                t0 = time.time()

                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    max_tokens=4096,
                )

                msg = response.choices[0].message

                # If no tool calls → final answer
                if not msg.tool_calls:
                    final_answer = msg.content or ""
                    # Auto-generate report if the LLM didn't call generate_pdf_report
                    if not self._report_generated:
                        logger.info("Agent finished without generating report — creating fallback report (run=%s)", self.run_id)
                        await self._generate_fallback_report(company_name, final_answer)
                    await self._finish_run(final_answer)
                    return final_answer

                # Execute each tool call
                messages.append(msg)  # assistant message with tool_calls

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    t_tool_start = time.time()
                    tool_output = await self._call_tool(tool_name, tool_input, company_name)
                    duration_ms = int((time.time() - t_tool_start) * 1000)

                    # Collect tool outputs for fallback report
                    if tool_name == "fetch_market_data" and "error" not in tool_output:
                        self._collected_data["market_data"] = tool_output
                    elif tool_name == "calculate_financial_ratios" and "error" not in tool_output:
                        self._collected_data["ratios"] = tool_output
                    elif tool_name == "fetch_news" and "error" not in tool_output:
                        headlines = tool_output.get("articles", [])
                        self._collected_data["news_headlines"] = [
                            a.get("title", "") for a in headlines
                        ] if isinstance(headlines, list) else []
                    elif tool_name == "create_alert":
                        self._collected_data.setdefault("alerts_summary", []).append(tool_output)

                    # Save tool call record
                    await self._save_tool_call(step, tool_name, tool_input, tool_output, duration_ms)

                    # Append tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_output),
                    })

            # Exceeded max iterations — still generate report if missing
            final_answer = "Analysis complete (reached max iterations)."
            if not self._report_generated:
                logger.info("Max iterations reached without report — creating fallback report (run=%s)", self.run_id)
                await self._generate_fallback_report(company_name, final_answer)
            await self._finish_run(final_answer)
            return final_answer

        except Exception as exc:
            error_msg = str(exc)
            logger.exception("Agent run %s failed: %s", self.run_id, error_msg)
            await self._fail_run(error_msg)
            raise

    async def _call_tool(self, tool_name: str, tool_input: dict, company_name: str) -> dict:
        """Dispatch a tool call and return its output."""
        try:
            if tool_name == "rag_search":
                return rag_search(
                    query=tool_input["query"],
                    company_id=tool_input.get("company_id", self.company_id),
                )
            elif tool_name == "fetch_market_data":
                return fetch_market_data(ticker=tool_input["ticker"])
            elif tool_name == "fetch_news":
                return fetch_news(
                    company_name=tool_input.get("company_name", company_name),
                    ticker=tool_input.get("ticker", ""),
                )
            elif tool_name == "calculate_financial_ratios":
                return calculate_financial_ratios(data=tool_input.get("data", {}))
            elif tool_name == "create_alert":
                # Always use the real company_id and run_id — ignore whatever the LLM provides
                return await create_alert(
                    company_id=str(self.company_id),
                    run_id=str(self.run_id),
                    level=tool_input.get("level", "info"),
                    message=tool_input.get("message", ""),
                    details=tool_input.get("details", {}),
                    db=self.db,
                )
            elif tool_name == "generate_pdf_report":
                file_path = generate_pdf_report(
                    content=tool_input.get("content", {}),
                    company_name=tool_input.get("company_name", company_name),
                    run_id=str(self.run_id),
                    reports_dir=settings.REPORTS_DIR,
                )
                # Save report record to database
                if file_path:
                    # Always store absolute path so download endpoint can find the file
                    abs_path = str(Path(file_path).resolve())
                    report = Report(
                        run_id=self.run_id,
                        company_id=uuid.UUID(self.company_id),
                        title=f"Financial Analysis Report - {company_name}",
                        file_path=abs_path,
                    )
                    if self.user_id:
                        report.created_by = uuid.UUID(self.user_id)
                    self.db.add(report)
                    await self.db.commit()
                    await self.db.refresh(report)
                    self._report_generated = True
                    logger.info("Saved report record %s -> %s", report.id, abs_path)
                    return {
                        "report_id": str(report.id),
                        "file_path": abs_path,
                        "title": report.title,
                        "status": "saved",
                    }
                return {"error": "PDF generation failed", "status": "failed"}
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error("Tool %s failed: %s", tool_name, e)
            return {"error": str(e)}

    async def _save_tool_call(
        self, step: int, tool_name: str, tool_input: dict, tool_output: dict, duration_ms: int
    ) -> None:
        tc = ToolCall(
            run_id=self.run_id,
            step=step,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            duration_ms=duration_ms,
        )
        self.db.add(tc)
        await self.db.commit()

    async def _generate_fallback_report(
        self, company_name: str, final_answer: str = "",
    ) -> None:
        """Generate a report automatically when the LLM didn't call generate_pdf_report."""
        try:
            content = dict(self._collected_data)
            # Use the final answer as the summary if available
            if final_answer:
                content.setdefault("summary", final_answer)
            if not content.get("summary"):
                content["summary"] = f"Financial analysis of {company_name}."

            file_path = generate_pdf_report(
                content=content,
                company_name=company_name,
                run_id=str(self.run_id),
                reports_dir=settings.REPORTS_DIR,
            )
            if file_path:
                abs_path = str(Path(file_path).resolve())
                report = Report(
                    run_id=self.run_id,
                    company_id=uuid.UUID(self.company_id),
                    title=f"Financial Analysis Report - {company_name}",
                    file_path=abs_path,
                )
                if self.user_id:
                    report.created_by = uuid.UUID(self.user_id)
                self.db.add(report)
                await self.db.commit()
                await self.db.refresh(report)
                self._report_generated = True
                logger.info("Fallback report saved: %s -> %s", report.id, abs_path)
            else:
                logger.error("Fallback report PDF generation also failed (run=%s)", self.run_id)
        except Exception as e:
            logger.exception("Failed to generate fallback report (run=%s): %s", self.run_id, e)

    async def _finish_run(self, final_answer: str) -> None:
        from sqlalchemy import select
        result = await self.db.execute(select(AgentRun).where(AgentRun.id == self.run_id))
        run = result.scalar_one_or_none()
        if run:
            run.status = "done"
            run.final_answer = final_answer
            run.finished_at = datetime.utcnow()
            await self.db.commit()

    async def _fail_run(self, error_message: str) -> None:
        from sqlalchemy import select
        result = await self.db.execute(select(AgentRun).where(AgentRun.id == self.run_id))
        run = result.scalar_one_or_none()
        if run:
            run.status = "failed"
            run.error_message = error_message
            run.finished_at = datetime.utcnow()
            await self.db.commit()
