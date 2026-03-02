from __future__ import annotations

import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


async def create_alert(
    company_id: str,
    run_id: str,
    level: str,
    message: str,
    details: dict,
    db,
) -> dict:
    """Save an alert to the database.

    Args:
        level: "info" | "warning" | "critical"
    """
    from backend.models.alert import Alert

    # ---------- Validate UUIDs before hitting the DB ----------
    try:
        validated_company_id = uuid.UUID(str(company_id))
    except (ValueError, AttributeError):
        logger.error("Invalid company_id UUID: %s", company_id)
        return {"error": f"Invalid company_id UUID: {company_id}"}

    try:
        validated_run_id = uuid.UUID(str(run_id))
    except (ValueError, AttributeError):
        logger.error("Invalid run_id UUID: %s", run_id)
        return {"error": f"Invalid run_id UUID: {run_id}"}

    # ---------- Validate level ----------
    if level not in ("info", "warning", "critical"):
        level = "info"

    try:
        alert = Alert(
            company_id=validated_company_id,
            run_id=validated_run_id,
            level=level,
            message=message,
            details=details,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        logger.info("Created %s alert: %s", level, message)
        return {"alert_id": str(alert.id), "status": "created"}
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create alert: %s", e)
        return {"error": str(e)}
