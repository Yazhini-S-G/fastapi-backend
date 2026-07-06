from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, desc, func, select

from app.constants import (
    BLOG_STATUS_APPROVED,
    BLOG_STATUS_DRAFT,
    BLOG_STATUS_PENDING_REVIEW,
    BLOG_STATUS_PUBLISHED,
    BLOG_STATUS_REJECTED,
)
from app.core.database import DBSessionDep
from app.models.audit_log import AuditLog
from app.models.blog import Blog
from app.models.user import User
from app.router.auth import get_current_user

router = APIRouter(prefix="/user-dashboard", tags=["user-dashboard"])


@router.get("/stats")
async def get_user_stats(
    current_user: Annotated[User, Depends(get_current_user)], db: DBSessionDep
) -> dict[str, int]:
    uid = current_user.id

    total_blogs = await db.scalar(select(func.count(Blog.id)).where(Blog.author_id == uid)) or 0
    published_blogs = (
        await db.scalar(
            select(func.count(Blog.id)).where(Blog.author_id == uid, Blog.status == BLOG_STATUS_PUBLISHED)
        )
        or 0
    )
    pending_blogs = (
        await db.scalar(
            select(func.count(Blog.id)).where(
                Blog.author_id == uid, Blog.status == BLOG_STATUS_PENDING_REVIEW
            )
        )
        or 0
    )
    draft_blogs = (
        await db.scalar(
            select(func.count(Blog.id)).where(Blog.author_id == uid, Blog.status == BLOG_STATUS_DRAFT)
        )
        or 0
    )
    rejected_blogs = (
        await db.scalar(
            select(func.count(Blog.id)).where(Blog.author_id == uid, Blog.status == BLOG_STATUS_REJECTED)
        )
        or 0
    )
    approved_blogs = (
        await db.scalar(
            select(func.count(Blog.id)).where(Blog.author_id == uid, Blog.status == BLOG_STATUS_APPROVED)
        )
        or 0
    )

    today = datetime.now(timezone.utc).date()
    blogs_today = (
        await db.scalar(
            select(func.count(Blog.id)).where(Blog.author_id == uid, cast(Blog.created_at, Date) == today)
        )
        or 0
    )

    return {
        "total_blogs": total_blogs,
        "published_blogs": published_blogs,
        "pending_blogs": pending_blogs,
        "draft_blogs": draft_blogs,
        "rejected_blogs": rejected_blogs,
        "approved_blogs": approved_blogs,
        "blogs_today": blogs_today,
    }


@router.get("/recent-activity")
async def get_user_recent_activity(
    current_user: Annotated[User, Depends(get_current_user)], db: DBSessionDep
) -> list[dict[str, object]]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .order_by(desc(AuditLog.created_at))
        .limit(15)
    )
    return [
        {
            "action": log.action_type,
            "module": log.module,
            "description": log.description,
            "timestamp": log.created_at,
            "status": log.status,
        }
        for log in result.scalars().all()
    ]
