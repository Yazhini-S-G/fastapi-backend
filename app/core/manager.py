from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import DBSessionManager, engine
from app.core.email import validate_smtp_config_for_startup
from app.models import Base
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User

DEFAULT_PERMISSIONS = [
    "create_user",
    "view_user",
    "edit_user",
    "delete_user",
    "view_reports",
    "manage_roles",
    "create_blog",
    "view_blog",
    "edit_own_blog",
    "upload_blog_image",
    "save_draft",
    "submit_for_review",
    "edit_blog",
    "delete_blog",
    "review_blog",
    "publish_blog",
    "feature_blog",
    "manage_blog_categories",
    "view_blog_analytics",
    "view_traffic_analytics",
    "view_session_reports",
    "export_csv_reports",
    "view_revenue_reports",
    "publish_article",
    "edit_any_article",
    "delete_article",
    "manage_comments",
    "add_new_product",
    "update_inventory",
    "process_refunds",
    "manage_discounts",
    "bypass_rate_limits",
    "access_premium_tools",
    "clear_system_cache",
    "view_audit_logs",
    "manage_ip_blacklist",
    "force_password_reset",
]

DEFAULT_ROLES = {
    "Super Admin": DEFAULT_PERMISSIONS,
    "Admin": [],
    "User": [
        "create_blog",
        "view_blog",
        "edit_own_blog",
        "upload_blog_image",
        "save_draft",
        "submit_for_review",
    ],
}

DEFAULT_BLOG_CATEGORIES = [
    "Technology",
    "Artificial Intelligence",
    "Machine Learning",
    "Programming",
    "Career",
    "Internship Experience",
    "Other",
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Handle startup and shutdown events, including DB table creation."""
    validate_smtp_config_for_startup()

    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("ALTER TYPE blog_status ADD VALUE IF NOT EXISTS 'Approved'")
        )
        await conn.execute(text("ALTER TABLE blogs ADD COLUMN IF NOT EXISTS tags TEXT"))
        await conn.execute(
            text(
                "ALTER TABLE blogs ADD COLUMN IF NOT EXISTS "
                "is_featured BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
    await seed_rbac_defaults()
    yield
    await engine.dispose()


async def _ensure_role_permissions(
    db: AsyncSession,
    role: Role,
    role_permissions: list[str],
    permissions: dict[str, Permission],
) -> None:
    for permission_name in role_permissions:
        permission = permissions[permission_name]
        exists_result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
        )
        if exists_result.scalar_one_or_none() is None:
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))


async def seed_rbac_defaults() -> None:
    from app.models.blog import BlogCategory

    async with DBSessionManager.session() as db:
        await deduplicate_seed_rows(db)

        permissions: dict[str, Permission] = {}
        for permission_name in DEFAULT_PERMISSIONS:
            perm_result = await db.execute(
                select(Permission).where(Permission.permission_name == permission_name)
            )
            permission = perm_result.scalar_one_or_none()
            if permission is None:
                permission = Permission(
                    permission_name=permission_name,
                    description=permission_name.replace("_", " ").title()
                )
                db.add(permission)
                await db.flush()
            permissions[permission_name] = permission

        roles: dict[str, Role] = {}
        for role_name, role_permissions in DEFAULT_ROLES.items():
            role_result = await db.execute(select(Role).where(Role.role_name == role_name))
            role = role_result.scalar_one_or_none()
            if role is None:
                role = Role(role_name=role_name, description=f"{role_name} role")
                db.add(role)
                await db.flush()
            roles[role_name] = role

            await _ensure_role_permissions(db, role, role_permissions, permissions)

        for category_name in DEFAULT_BLOG_CATEGORIES:
            category = await db.scalar(select(BlogCategory).where(BlogCategory.name == category_name))
            if category is None:
                db.add(BlogCategory(name=category_name))

        users_without_roles = await db.execute(
            select(User)
            .outerjoin(UserRole, UserRole.user_id == User.id)
            .where(UserRole.id.is_(None))
            .order_by(User.id.asc())
        )
        for index, user in enumerate(users_without_roles.scalars().all()):
            role_name = "Super Admin" if index == 0 else "User"
            db.add(UserRole(user_id=user.id, role_id=roles[role_name].id))

        await db.commit()


async def _delete_duplicate_dependencies(
    db: AsyncSession,
    model: type[Permission] | type[Role],
    duplicate: Base,
) -> None:
    if model is Permission:
        await db.execute(
            delete(RolePermission).where(
                RolePermission.permission_id == cast("Permission", duplicate).id
            )
        )
        return

    role_id = cast("Role", duplicate).id
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    await db.execute(delete(UserRole).where(UserRole.role_id == role_id))


async def deduplicate_seed_rows(db: AsyncSession) -> None:
    for model, column in (
        (Permission, Permission.permission_name),
        (Role, Role.role_name),
    ):
        names = await db.execute(select(column).group_by(column).having(func.count(model.id) > 1))
        for name in names.scalars().all():
            rows = await db.execute(select(model).where(column == name).order_by(model.id.asc()))
            for duplicate in rows.scalars().all()[1:]:
                await _delete_duplicate_dependencies(db, model, duplicate)
                await db.delete(duplicate)

    for link_model, first_col, second_col in (
        (RolePermission, RolePermission.role_id, RolePermission.permission_id),
        (UserRole, UserRole.user_id, UserRole.role_id),
    ):
        link_model_id = cast("type[RolePermission]", link_model).id
        duplicates = await db.execute(
            select(func.min(link_model_id), first_col, second_col)
            .group_by(first_col, second_col)
            .having(func.count(link_model_id) > 1)
        )
        for keep_id, first_id, second_id in duplicates.all():
            await db.execute(
                delete(link_model).where(
                    first_col == first_id,
                    second_col == second_id,
                    link_model_id != keep_id,
                )
            )

    await db.flush()
