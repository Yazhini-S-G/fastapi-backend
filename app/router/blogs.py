import os
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from anyio import Path
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.constants import (
    ACCESS_DENIED_DETAIL,
    ACTION_APPROVE_BLOG,
    ACTION_CREATE_BLOG,
    ACTION_DELETE_BLOG,
    ACTION_PUBLISH_BLOG,
    ACTION_SUBMIT_BLOG_FOR_REVIEW,
    ACTION_UPDATE_BLOG,
    BLOG_STATUS_APPROVED,
    BLOG_STATUS_DRAFT,
    BLOG_STATUS_PENDING_REVIEW,
    BLOG_STATUS_PUBLISHED,
    BLOG_STATUS_REJECTED,
    MODULE_BLOG_MANAGEMENT,
    PERM_CREATE_BLOG,
    PERM_DELETE_BLOG,
    PERM_EDIT_BLOG,
    PERM_EDIT_OWN_BLOG,
    PERM_FEATURE_BLOG,
    PERM_PUBLISH_BLOG,
    PERM_REVIEW_BLOG,
    PERM_SAVE_DRAFT,
    PERM_SUBMIT_FOR_REVIEW,
    PERM_UPLOAD_BLOG_IMAGE,
    PERM_VIEW_BLOG,
    PERM_VIEW_BLOG_ANALYTICS,
    ROLE_SUPER_ADMIN,
    ROLE_USER,
)
from app.core.audit_logger import log_audit_event
from app.core.database import DBSessionDep
from app.core.rbac import get_user_role_names, user_has_permission
from app.models.blog import Blog, BlogCategory
from app.models.user import User
from app.router.auth import get_current_user
from app.schema.blog import (
    BlogAnalyticsOut,
    BlogCategoryOut,
    BlogCreateRequest,
    BlogOut,
    BlogStatusRequest,
    BlogUpdateRequest,
)

router = APIRouter(prefix="/blogs", tags=["blogs"])
PENDING_REVIEW = BLOG_STATUS_PENDING_REVIEW
BLOG_MANAGEMENT = MODULE_BLOG_MANAGEMENT
SUBMIT_BLOG_FOR_REVIEW = ACTION_SUBMIT_BLOG_FOR_REVIEW


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_STATUSES = {
    BLOG_STATUS_DRAFT,
    PENDING_REVIEW,
    BLOG_STATUS_APPROVED,
    BLOG_STATUS_PUBLISHED,
    BLOG_STATUS_REJECTED,
}


def full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.email


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def is_super_admin(db: DBSessionDep, user: User) -> bool:
    return ROLE_SUPER_ADMIN in await get_user_role_names(db, user.id)


async def require_blog_permission(db: DBSessionDep, user: User, permission_name: str) -> None:
    if not await user_has_permission(db, user.id, permission_name):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_DETAIL)


async def can_edit_blog(db: DBSessionDep, user: User, blog: Blog) -> bool:
    if await user_has_permission(db, user.id, PERM_EDIT_BLOG):
        return True
    return blog.author_id == user.id and await user_has_permission(db, user.id, PERM_EDIT_OWN_BLOG)


async def get_actor_label(db: DBSessionDep, user: User) -> str:
    roles = await get_user_role_names(db, user.id)
    role = roles[0] if roles else ROLE_USER
    return f"{full_name(user)} ({role})"


def serialize_blog(blog: Blog) -> BlogOut:
    def _name(u: User | None) -> str | None:
        return full_name(u) if u else None

    return BlogOut(
        id=blog.id,
        title=blog.title,
        content=blog.content,
        featured_image=blog.featured_image,
        author_id=blog.author_id,
        author_name=full_name(blog.author),
        status=blog.status,
        category_id=blog.category_id,
        category_name=blog.category.name if blog.category else None,
        tags=blog.tags or "",
        is_featured=bool(blog.is_featured),
        created_at=blog.created_at,
        updated_at=blog.updated_at,
        approved_by_name=_name(blog.approved_by) if blog.approved_by_id else None,
        approved_at=blog.approved_at,
        published_by_name=_name(blog.published_by) if blog.published_by_id else None,
        published_at=blog.published_at,
    )


BLOG_LOAD_OPTIONS = [
    selectinload(Blog.author),
    selectinload(Blog.category),
    selectinload(Blog.approved_by),
    selectinload(Blog.published_by),
]


async def get_blog_or_404(db: DBSessionDep, blog_id: int) -> Blog:
    blog = await db.scalar(select(Blog).options(*BLOG_LOAD_OPTIONS).where(Blog.id == blog_id))
    if blog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog not found")
    return blog


def status_for_action(action: str) -> str:
    return {"submit": PENDING_REVIEW, "publish": BLOG_STATUS_PUBLISHED}.get(action, BLOG_STATUS_DRAFT)


@router.get("/categories")
async def list_categories(db: DBSessionDep) -> list[BlogCategoryOut]:
    result = await db.execute(select(BlogCategory).order_by(BlogCategory.name))
    return [BlogCategoryOut(id=c.id, name=c.name, description=c.description) for c in result.scalars().all()]


@router.get("")
async def list_blogs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
    search: str = "",
    status_filter: str = "",
    category_id: int | None = None,
) -> list[BlogOut]:
    await require_blog_permission(db, current_user, PERM_VIEW_BLOG)
    query = select(Blog).options(*BLOG_LOAD_OPTIONS).order_by(Blog.id.desc())
    is_admin = await is_super_admin(db, current_user)
    can_review = await user_has_permission(db, current_user.id, PERM_REVIEW_BLOG)
    if not is_admin and not can_review:
        query = query.where(Blog.author_id == current_user.id)
    if search:
        like = f"%{search}%"
        query = query.join(User, User.id == Blog.author_id).where(
            or_(
                Blog.title.ilike(like),
                Blog.tags.ilike(like),
                User.email.ilike(like),
                User.first_name.ilike(like),
            )
        )
    if status_filter:
        query = query.where(Blog.status == status_filter)
    if category_id:
        query = query.where(Blog.category_id == category_id)
    result = await db.execute(query)
    return [serialize_blog(b) for b in result.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_blog(
    request: Request,
    payload: BlogCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> BlogOut:
    await require_blog_permission(db, current_user, PERM_CREATE_BLOG)
    target_status = status_for_action(payload.action)
    if target_status == BLOG_STATUS_PUBLISHED:
        await require_blog_permission(db, current_user, PERM_PUBLISH_BLOG)
    elif target_status == PENDING_REVIEW:
        await require_blog_permission(db, current_user, PERM_SUBMIT_FOR_REVIEW)
    else:
        await require_blog_permission(db, current_user, PERM_SAVE_DRAFT)

    blog = Blog(
        title=payload.title.strip(),
        content=payload.content,
        featured_image=payload.featured_image,
        author_id=current_user.id,
        category_id=payload.category_id,
        tags=payload.tags,
        status=target_status,
    )
    db.add(blog)
    await db.flush()

    actor = await get_actor_label(db, current_user)
    log_audit_event(
        db,
        current_user,
        ACTION_CREATE_BLOG,
        BLOG_MANAGEMENT,
        f'{actor} created blog "{blog.title}" (Blog ID: {blog.id})',
        request,
    )
    if target_status == PENDING_REVIEW:
        log_audit_event(
            db,
            current_user,
            SUBMIT_BLOG_FOR_REVIEW,
            BLOG_MANAGEMENT,
            f'{actor} submitted blog "{blog.title}" for review (Blog ID: {blog.id})',
            request,
        )

    blog_id = blog.id
    await db.commit()
    return serialize_blog(await get_blog_or_404(db, blog_id))


@router.put("/{blog_id}")
async def update_blog(
    request: Request,
    blog_id: int,
    payload: BlogUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> BlogOut:
    blog = await get_blog_or_404(db, blog_id)
    if not await can_edit_blog(db, current_user, blog):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_DETAIL)

    old_status = blog.status
    target_status = status_for_action(payload.action)
    if target_status == BLOG_STATUS_PUBLISHED:
        await require_blog_permission(db, current_user, PERM_PUBLISH_BLOG)
    elif target_status == PENDING_REVIEW:
        await require_blog_permission(db, current_user, PERM_SUBMIT_FOR_REVIEW)

    blog.title = payload.title.strip()
    blog.content = payload.content
    blog.featured_image = payload.featured_image
    blog.category_id = payload.category_id
    blog.tags = payload.tags
    blog.status = target_status

    actor = await get_actor_label(db, current_user)
    log_audit_event(
        db,
        current_user,
        ACTION_UPDATE_BLOG,
        BLOG_MANAGEMENT,
        f'{actor} edited blog "{blog.title}" (Blog ID: {blog_id})',
        request,
    )
    if target_status == PENDING_REVIEW and old_status != PENDING_REVIEW:
        log_audit_event(
            db,
            current_user,
            SUBMIT_BLOG_FOR_REVIEW,
            BLOG_MANAGEMENT,
            f'{actor} submitted blog "{blog.title}" for review (Blog ID: {blog_id})',
            request,
        )

    await db.commit()
    return serialize_blog(await get_blog_or_404(db, blog_id))


@router.put("/{blog_id}/status")
async def update_blog_status(
    request: Request,
    blog_id: int,
    payload: BlogStatusRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> BlogOut:
    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    await require_blog_permission(
        db, current_user, PERM_PUBLISH_BLOG if payload.status == BLOG_STATUS_PUBLISHED else PERM_REVIEW_BLOG
    )

    blog = await get_blog_or_404(db, blog_id)
    original_author = full_name(blog.author)
    actor = await get_actor_label(db, current_user)

    blog.status = payload.status

    # Populate lifecycle actor + timestamp
    ts = now_utc()
    if payload.status == BLOG_STATUS_APPROVED:
        blog.approved_by_id = current_user.id
        blog.approved_at = ts
    elif payload.status == BLOG_STATUS_PUBLISHED:
        blog.published_by_id = current_user.id
        blog.published_at = ts

    blog_title = blog.title
    action_map = {
        BLOG_STATUS_APPROVED: (
            ACTION_APPROVE_BLOG,
            f'{actor} approved blog "{blog_title}" created by {original_author} (Blog ID: {blog_id})',
        ),
        BLOG_STATUS_REJECTED: (
            "Reject Blog",
            f'{actor} rejected blog "{blog_title}" created by {original_author} (Blog ID: {blog_id})',
        ),
        BLOG_STATUS_PUBLISHED: (
            ACTION_PUBLISH_BLOG,
            f'{actor} published blog "{blog_title}" created by {original_author} (Blog ID: {blog_id})',
        ),
        PENDING_REVIEW: (
            SUBMIT_BLOG_FOR_REVIEW,
            f'{actor} submitted blog "{blog_title}" for review (Blog ID: {blog_id})',
        ),
        BLOG_STATUS_DRAFT: (
            "Unpublish Blog",
            f'{actor} moved blog "{blog_title}" back to Draft (Blog ID: {blog_id})',
        ),
    }
    action, description = action_map.get(
        payload.status, ("Change Blog Status", f'{actor} changed blog "{blog.title}" to {payload.status}')
    )

    log_audit_event(db, current_user, action, BLOG_MANAGEMENT, description, request)
    await db.commit()
    return serialize_blog(await get_blog_or_404(db, blog_id))


@router.put("/{blog_id}/feature")
async def feature_blog(
    blog_id: int, current_user: Annotated[User, Depends(get_current_user)], db: DBSessionDep
) -> BlogOut:
    await require_blog_permission(db, current_user, PERM_FEATURE_BLOG)
    blog = await get_blog_or_404(db, blog_id)
    blog.is_featured = not blog.is_featured
    await db.commit()
    return serialize_blog(await get_blog_or_404(db, blog_id))


@router.delete("/{blog_id}")
async def delete_blog(
    request: Request, blog_id: int, current_user: Annotated[User, Depends(get_current_user)], db: DBSessionDep
) -> dict[str, str]:
    blog = await get_blog_or_404(db, blog_id)
    if blog.author_id != current_user.id:
        await require_blog_permission(db, current_user, PERM_DELETE_BLOG)
    elif not await user_has_permission(db, current_user.id, PERM_DELETE_BLOG):
        await require_blog_permission(db, current_user, "delete_own_blog")

    actor = await get_actor_label(db, current_user)
    original_author = full_name(blog.author)
    title = blog.title

    await db.delete(blog)
    log_audit_event(
        db,
        current_user,
        ACTION_DELETE_BLOG,
        BLOG_MANAGEMENT,
        f'{actor} deleted blog "{title}" created by {original_author} (Blog ID: {blog_id})',
        request,
    )
    await db.commit()
    return {"message": "Blog deleted successfully"}


@router.post("/upload-image")
async def upload_blog_image(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
    file: Annotated[UploadFile, File()],
) -> dict[str, str]:
    await require_blog_permission(db, current_user, PERM_UPLOAD_BLOG_IMAGE)
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPG, JPEG, PNG, and WEBP are allowed"
        )
    upload_dir = Path(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "blogs"))
    )
    await upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{ext}"
    destination = upload_dir / filename
    await destination.write_bytes(await file.read())
    return {"path": f"/uploads/blogs/{filename}"}


@router.get("/analytics")
async def blog_analytics(
    current_user: Annotated[User, Depends(get_current_user)], db: DBSessionDep
) -> BlogAnalyticsOut:
    await require_blog_permission(db, current_user, PERM_VIEW_BLOG_ANALYTICS)
    total = await db.scalar(select(func.count(Blog.id))) or 0
    published = await db.scalar(select(func.count(Blog.id)).where(Blog.status == BLOG_STATUS_PUBLISHED)) or 0
    pending = await db.scalar(select(func.count(Blog.id)).where(Blog.status == PENDING_REVIEW)) or 0
    rejected = await db.scalar(select(func.count(Blog.id)).where(Blog.status == BLOG_STATUS_REJECTED)) or 0
    draft = await db.scalar(select(func.count(Blog.id)).where(Blog.status == BLOG_STATUS_DRAFT)) or 0
    authors = await db.execute(
        select(User.email, func.count(Blog.id))
        .join(Blog, Blog.author_id == User.id)
        .group_by(User.email)
        .order_by(func.count(Blog.id).desc())
        .limit(5)
    )
    cats = await db.execute(
        select(BlogCategory.name, func.count(Blog.id))
        .join(Blog, Blog.category_id == BlogCategory.id, isouter=True)
        .group_by(BlogCategory.name)
        .order_by(func.count(Blog.id).desc())
    )
    recent = await db.execute(select(Blog).options(*BLOG_LOAD_OPTIONS).order_by(Blog.id.desc()).limit(5))
    return BlogAnalyticsOut(
        total_blogs=total,
        published_blogs=published,
        pending_blogs=pending,
        rejected_blogs=rejected,
        draft_blogs=draft,
        most_active_authors=[{"author": e, "count": c} for e, c in authors.all()],
        recent_blogs=[serialize_blog(b) for b in recent.scalars().all()],
        blogs_by_category=[{"category": n or "Uncategorized", "count": c} for n, c in cats.all()],
    )
