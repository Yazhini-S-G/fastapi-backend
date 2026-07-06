from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select

from app.constants import ACCESS_DENIED_DETAIL, ROLE_SUPER_ADMIN
from app.core.database import DBSessionDep
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.models.user_permission import UserPermission


async def get_user_role_names(db: DBSessionDep, user_id: int) -> list[str]:
    result = await db.execute(
        select(Role.role_name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .order_by(Role.role_name)
    )
    return list(result.scalars().all())


async def get_user_permissions(db: DBSessionDep, user_id: int) -> list[str]:
    role_names = await get_user_role_names(db, user_id)
    if ROLE_SUPER_ADMIN in role_names:
        result = await db.execute(select(Permission.permission_name).order_by(Permission.permission_name))
        return list(result.scalars().all())

    # Permissions from roles
    role_perms = await db.execute(
        select(Permission.permission_name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )

    # Direct user permissions (from user_permissions table)
    direct_perms = await db.execute(
        select(Permission.permission_name)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user_id)
        .distinct()
    )

    combined = set(role_perms.scalars().all()) | set(direct_perms.scalars().all())
    return sorted(combined)


async def user_has_permission(db: DBSessionDep, user_id: int, permission_name: str) -> bool:
    role_names = await get_user_role_names(db, user_id)
    if ROLE_SUPER_ADMIN in role_names:
        return True
    permissions = await get_user_permissions(db, user_id)
    return permission_name in permissions


def require_permission(permission_name: str) -> Callable[..., object]:
    from app.router.auth import get_current_user

    async def dependency(current_user: Annotated[User, Depends(get_current_user)], db: DBSessionDep) -> User:
        if not await user_has_permission(db, current_user.id, permission_name):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_DETAIL)
        return current_user

    return dependency
