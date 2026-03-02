from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models for Alembic metadata
from backend.models.alert import Alert  # noqa: E402,F401
from backend.models.agent_run import AgentRun  # noqa: E402,F401
from backend.models.chunk import Chunk  # noqa: E402,F401
from backend.models.company import Company  # noqa: E402,F401
from backend.models.document import Document  # noqa: E402,F401
from backend.models.report import Report  # noqa: E402,F401
from backend.models.tool_call import ToolCall  # noqa: E402,F401
from backend.models.user import User  # noqa: E402,F401


