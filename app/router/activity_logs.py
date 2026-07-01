import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import Date, cast, desc, func, select

from app.core.database import DBSessionDep
from app.core.rbac import get_user_role_names
from app.models.audit_log import AuditLog
from app.models.user import User
from app.router.auth import get_current_user
from app.schema.activity_log import (
    ActivityLogsPaginated,
    ActivityStats,
    AdminSessionOut,
    AdminSessionPaginated,
    AuditLogResponse,
)

router = APIRouter(prefix="/activity-logs", tags=["activity-logs"])


async def require_super_admin(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> User:
    roles = await get_user_role_names(db, current_user.id)
    if "Super Admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied. Super Admin only.")
    return current_user


# ---------------------------------------------------------------------------
# Activity Logs
# ---------------------------------------------------------------------------

@router.get("")
async def get_activity_logs(
    _: Annotated[User, Depends(require_super_admin)],
    db: DBSessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    admin_name: str | None = None,
    admin_email: str | None = None,
    action_type: str | None = None,
    module: str | None = None,
    date: str | None = None,
) -> ActivityLogsPaginated:
    query = select(AuditLog)

    if admin_name:
        query = query.where(AuditLog.username.ilike(f"%{admin_name}%"))
    if admin_email:
        query = query.where(AuditLog.email.ilike(f"%{admin_email}%"))
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    if module:
        query = query.where(AuditLog.module == module)
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.where(cast(AuditLog.created_at, Date) == target_date)
        except ValueError:
            pass

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    paged = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * size).limit(size)
    result = await db.execute(paged)
    logs = result.scalars().all()

    return ActivityLogsPaginated(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        size=size,
        pages=max(1, (total + size - 1) // size) if total else 1,
    )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_activity_stats(
    _: Annotated[User, Depends(require_super_admin)],
    db: DBSessionDep,
) -> ActivityStats:
    today = datetime.now(timezone.utc).date()

    async def count_action(action: str) -> int:
        return await db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.action_type == action,
                cast(AuditLog.created_at, Date) == today,
            )
        ) or 0

    async def count_module(module: str) -> int:
        return await db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.module == module,
                cast(AuditLog.created_at, Date) == today,
            )
        ) or 0

    total_logins = await count_action("Login")
    failed_logins = await count_action("Failed Login")
    total_logouts = await count_action("Logout")
    active_sessions = max(0, total_logins - total_logouts)
    blogs_created = await count_action("Create Blog")
    blogs_edited = await count_action("Update Blog")
    blogs_deleted = await count_action("Delete Blog")
    blogs_published = await count_action("Publish Blog")
    blogs_approved = await count_action("Approve Blog")
    user_mgmt = await count_module("User Management")
    role_mgmt = await count_module("Role Management")

    # 7-day chart
    chart_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        count = await db.scalar(
            select(func.count(AuditLog.id)).where(cast(AuditLog.created_at, Date) == d)
        ) or 0
        chart_data.append({"date": d.strftime("%b %d"), "actions": count})

    return ActivityStats(
        total_logins_today=total_logins,
        failed_logins_today=failed_logins,
        total_active_sessions=active_sessions,
        blogs_created_today=blogs_created,
        blogs_edited_today=blogs_edited,
        blogs_deleted_today=blogs_deleted,
        blogs_published_today=blogs_published,
        blogs_approved_today=blogs_approved,
        user_management_actions=user_mgmt,
        role_permission_changes=role_mgmt,
        activity_chart_data=chart_data,
    )


# ---------------------------------------------------------------------------
# Blog history (per-blog timeline)
# ---------------------------------------------------------------------------

@router.get("/blog-history/{blog_id}")
async def get_blog_history(
    blog_id: int,
    _: Annotated[User, Depends(require_super_admin)],
    db: DBSessionDep,
) -> list[dict[str, object]]:
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.module == "Blog Management",
            AuditLog.description.ilike(f"%Blog ID: {blog_id}%"),
        )
        .order_by(AuditLog.created_at.asc())
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action_type,
            "actor": log.username,
            "email": log.email,
            "description": log.description,
            "status": log.status,
            "timestamp": log.created_at,
            "ip_address": log.ip_address,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

@router.get("/export")
async def export_activity_logs(
    _: Annotated[User, Depends(require_super_admin)],
    db: DBSessionDep,
) -> Response:
    result = await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)))
    logs = result.scalars().all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "User ID", "Username", "Email", "Module",
        "Action Type", "Description", "IP Address", "Status", "Timestamp"
    ])
    for log in logs:
        writer.writerow([
            log.id,
            log.user_id or "",
            log.username,
            log.email or "",
            log.module,
            log.action_type,
            log.description,
            log.ip_address or "",
            log.status,
            log.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if log.created_at else "",
        ])

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=audit_log_export.csv"
    return response


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def _format_session_duration(login_time: datetime, logout_time: datetime | None) -> str | None:
    if logout_time is None:
        return None

    seconds = int((logout_time - login_time).total_seconds())
    if seconds <= 0:
        return None

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


async def _build_admin_session(db: DBSessionDep, log: AuditLog) -> AdminSessionOut:
    logout_log = await db.scalar(
        select(AuditLog)
        .where(
            AuditLog.user_id == log.user_id,
            AuditLog.action_type == "Logout",
            AuditLog.created_at >= log.created_at,
        )
        .order_by(AuditLog.created_at.asc())
        .limit(1)
    )
    logout_time = logout_log.created_at if logout_log else None
    return AdminSessionOut(
        admin_name=log.username,
        admin_email=log.email,
        login_time=log.created_at,
        logout_time=logout_time,
        session_duration=_format_session_duration(log.created_at, logout_time),
        ip_address=log.ip_address,
        is_active=logout_time is None,
    )


@router.get("/sessions")
async def get_admin_sessions(
    _: Annotated[User, Depends(require_super_admin)],
    db: DBSessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminSessionPaginated:
    login_query = select(AuditLog).where(AuditLog.action_type == "Login").order_by(desc(AuditLog.created_at))
    total = await db.scalar(select(func.count()).select_from(login_query.subquery())) or 0
    result = await db.execute(login_query.offset((page - 1) * size).limit(size))
    login_logs = result.scalars().all()

    items = [await _build_admin_session(db, log) for log in login_logs]

    return AdminSessionPaginated(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=max(1, (total + size - 1) // size) if total else 1,
    )
