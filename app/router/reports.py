from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, desc, func, select

from app.core.database import DBSessionDep
from app.core.rbac import require_permission
from app.models.audit_log import AuditLog
from app.models.blog import Blog
from app.models.role import Role, UserRole
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
async def get_summary(
    _: Annotated[User, Depends(require_permission("view_reports"))],
    db: DBSessionDep,
) -> dict[str, dict[str, int]]:
    today = datetime.now(timezone.utc).date()

    # User statistics
    total_users = await db.scalar(select(func.count(User.id))) or 0
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    inactive_users = total_users - active_users
    admins = await db.scalar(
        select(func.count(UserRole.user_id.distinct()))
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.role_name == "Admin")
    ) or 0
    super_admins = await db.scalar(
        select(func.count(UserRole.user_id.distinct()))
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.role_name == "Super Admin")
    ) or 0

    # Blog statistics
    total_blogs = await db.scalar(select(func.count(Blog.id))) or 0
    published_blogs = await db.scalar(select(func.count(Blog.id)).where(Blog.status == "Published")) or 0
    pending_blogs = await db.scalar(select(func.count(Blog.id)).where(Blog.status == "Pending Review")) or 0
    draft_blogs = await db.scalar(select(func.count(Blog.id)).where(Blog.status == "Draft")) or 0
    rejected_blogs = await db.scalar(select(func.count(Blog.id)).where(Blog.status == "Rejected")) or 0

    # Activity statistics — from audit_logs
    logins_today = await db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action_type == "Login",
            cast(AuditLog.created_at, Date) == today,
        )
    ) or 0
    logouts_today = await db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action_type == "Logout",
            cast(AuditLog.created_at, Date) == today,
        )
    ) or 0
    failed_logins = await db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action_type == "Failed Login",
            cast(AuditLog.created_at, Date) == today,
        )
    ) or 0
    active_sessions = max(0, logins_today - logouts_today)
    user_actions_today = await db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.module == "User Management",
            cast(AuditLog.created_at, Date) == today,
        )
    ) or 0
    role_changes_today = await db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.module == "Role Management",
            cast(AuditLog.created_at, Date) == today,
        )
    ) or 0

    return {
        "user_statistics": {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "admins": admins,
            "super_admins": super_admins,
        },
        "blog_statistics": {
            "total_blogs": total_blogs,
            "published_blogs": published_blogs,
            "pending_blogs": pending_blogs,
            "draft_blogs": draft_blogs,
            "rejected_blogs": rejected_blogs,
        },
        "activity_statistics": {
            "total_logins_today": logins_today,
            "failed_logins_today": failed_logins,
            "active_sessions": active_sessions,
            "user_actions_today": user_actions_today,
            "role_changes_today": role_changes_today,
        },
    }


@router.get("/recent")
async def get_recent(
    _: Annotated[User, Depends(require_permission("view_reports"))],
    db: DBSessionDep,
) -> list[dict[str, object]]:
    result = await db.execute(
        select(AuditLog).order_by(desc(AuditLog.created_at)).limit(20)
    )
    return [
        {
            "username": log.username,
            "email": log.email,
            "action": log.action_type,
            "module": log.module,
            "description": log.description,
            "status": log.status,
            "timestamp": log.created_at,
        }
        for log in result.scalars().all()
    ]


@router.get("/charts")
async def get_charts(
    _: Annotated[User, Depends(require_permission("view_reports"))],
    db: DBSessionDep,
) -> dict[str, list[dict[str, object]]]:
    today = datetime.now(timezone.utc).date()

    # User growth: new users per month (last 6 months from audit logs)
    user_growth = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        if i == 0:
            month_end = today
        else:
            next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = next_month - timedelta(days=1)
        count = await db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.action_type == "Create User",
                cast(AuditLog.created_at, Date) >= month_start,
                cast(AuditLog.created_at, Date) <= month_end,
            )
        ) or 0
        user_growth.append({"name": month_start.strftime("%b %Y"), "count": count})

    # Blog growth: blogs created last 7 days
    blog_growth = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        count = await db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.action_type == "Create Blog",
                cast(AuditLog.created_at, Date) == d,
            )
        ) or 0
        blog_growth.append({"name": d.strftime("%b %d"), "count": count})

    # Role distribution — users per role (exclude Custom roles)
    role_dist_result = await db.execute(
        select(Role.role_name, func.count(UserRole.user_id.distinct()).label("count"))
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            ~Role.role_name.like("User Custom %"),
            ~Role.role_name.like("Admin Custom %"),
        )
        .group_by(Role.role_name)
        .order_by(func.count(UserRole.user_id.distinct()).desc())
    )
    role_distribution = [
        {"name": name, "count": count}
        for name, count in role_dist_result.all()
    ]

    # Most active users (by audit log entries this month)
    month_start = today.replace(day=1)
    top_users_result = await db.execute(
        select(AuditLog.username, func.count(AuditLog.id).label("actions"))
        .where(cast(AuditLog.created_at, Date) >= month_start)
        .group_by(AuditLog.username)
        .order_by(func.count(AuditLog.id).desc())
        .limit(5)
    )
    top_users = [{"username": u, "actions": c} for u, c in top_users_result.all()]

    return {
        "user_growth": user_growth,
        "blog_growth": blog_growth,
        "role_distribution": role_distribution,
        "top_users": top_users,
    }
