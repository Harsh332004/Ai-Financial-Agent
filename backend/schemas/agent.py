from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class AgentRunCreate(BaseModel):
    task: str = Field(
        ...,
        description="Natural-language task for the agent to perform",
        example="Analyze Apple's financial health and flag any significant risks.",
    )
    company_id: uuid.UUID = Field(..., description="UUID of the company to analyze")


class AgentRunUpdate(BaseModel):
    status: str | None = Field(None, description="Updated status: running | done | failed")
    final_answer: str | None = Field(None, description="Agent's final written analysis")
    error_message: str | None = Field(None, description="Error detail if status=failed")
    finished_at: datetime | None = Field(None, description="Completion timestamp (UTC)")


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Tool call record ID")
    run_id: uuid.UUID | None = Field(None, description="Parent agent run ID")
    step: int = Field(..., description="Step number in the ReAct loop (0-indexed)")
    tool_name: str = Field(..., description="Name of the tool that was called", example="rag_search")
    tool_input: dict[str, Any] | None = Field(None, description="Arguments passed to the tool")
    tool_output: dict[str, Any] | None = Field(None, description="Result returned by the tool")
    duration_ms: int | None = Field(None, description="Time the tool took to execute (milliseconds)")
    called_at: datetime = Field(..., description="When this tool call was made (UTC)")


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Agent run unique identifier")
    user_id: uuid.UUID | None = Field(None, description="User who submitted the task")
    company_id: uuid.UUID | None = Field(None, description="Company being analyzed")
    task: str = Field(..., description="The original task description")
    status: str = Field(..., description="Current status: `running` | `done` | `failed`")
    final_answer: str | None = Field(None, description="Agent's final analysis text (available when status=done)")
    error_message: str | None = Field(None, description="Error details (available when status=failed)")
    started_at: datetime = Field(..., description="When the run started (UTC)")
    finished_at: datetime | None = Field(None, description="When the run completed (UTC)")


class AgentRunDetailResponse(AgentRunResponse):
    tool_calls: list[ToolCallResponse] = Field(
        default_factory=list,
        description="Full reasoning trace — every tool call the agent made in order",
    )
