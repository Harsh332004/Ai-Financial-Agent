from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.alert import Alert
from backend.models.user import User
from backend.schemas.alert import AlertResponse
from backend.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=list[AlertResponse],
    summary="List alerts",
    description=(
        "Returns risk alerts raised by agent runs, sorted newest first.\n\n"
        "**Filter options:**\n"
        "- `company_id` — alerts for a specific company\n"
        "- `level` — `info` | `warning` | `critical`\n"
        "- `acknowledged` — `true` to see resolved alerts, `false` for unresolved\n\n"
        "**Alert levels:**\n"
        "- 🔵 `info` — notable data point, no immediate action required\n"
        "- 🟡 `warning` — potential concern (e.g. declining revenue growth)\n"
        "- 🔴 `critical` — urgent risk (e.g. revenue decline >5%, very high debt-to-equity)"
    ),
    response_description="Array of alert records",
)
async def list_alerts(
    company_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
    level: str | None = None,
    acknowledged: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Alert]:
    query = select(Alert).order_by(Alert.created_at.desc())
    if company_id is not None:
        query = query.where(Alert.company_id == company_id)
    if run_id is not None:
        query = query.where(Alert.run_id == run_id)
    if level is not None:
        query = query.where(Alert.level == level)
    if acknowledged is not None:
        query = query.where(Alert.acknowledged == acknowledged)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.put(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an alert",
    description=(
        "Mark an alert as reviewed. Records the authenticated user as `acknowledged_by` "
        "and sets `acknowledged_at` to the current UTC timestamp.\n\n"
        "Returns **404** if the alert is not found."
    ),
    response_description="Updated alert with acknowledged=true",
)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    await db.commit()
    await db.refresh(alert)
    logger.info("Alert %s acknowledged by user %s", alert_id, current_user.id)
    return alert


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert",
    description=(
        "Permanently delete an alert record. "
        "Returns **204 No Content** on success, **404** if not found."
    ),
)
async def delete_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
    logger.info("Deleted alert %s", alert_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
