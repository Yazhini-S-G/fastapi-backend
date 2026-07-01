from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select

from app.core.audit_logger import log_audit_event
from app.core.database import DBSessionDep
from app.core.rbac import get_user_permissions, get_user_role_names, require_permission
from app.core.security import hash_password
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.models.user_permission import UserPermission
from app.router.auth import get_current_user
from app.schema.rbac import (
    DashboardStats,
    PermissionOut,
    PermissionUpdateRequest,
    RoleCreateRequest,
    RoleOut,
    RoleUpdateRequest,
    UserCreateRequest,
    UserOut,
    UserUpdateRequest,
)

router = APIRouter(prefix="/rbac", tags=["rbac"])

SUPER_ADMIN_ROLE = "Super Admin"
ADMIN_ROLE = "Admin"
USER_ROLE = "User"
MANAGE_ROLES_PERMISSION = "manage_roles"
ACCESS_DENIED_DETAIL = "Access Denied"
USER_NOT_FOUND_DETAIL = "User not found"
ROLE_NOT_FOUND_DETAIL = "Role not found"
USER_MANAGEMENT_AREA = "User Management"
ROLE_MANAGEMENT_AREA = "Role Management"
MODIFY_PERMISSIONS_ACTION = "Modify Permissions"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.email


async def serialize_user(db: DBSessionDep, user: User) -> UserOut:
    roles = await get_user_role_names(db, user.id)
    permissions = await get_user_permissions(db, user.id)
    return UserOut(
        id=user.id,
        name=full_name(user),
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        roles=roles,
        permissions=permissions,
    )


async def serialize_role(db: DBSessionDep, role: Role) -> RoleOut:
    result = await db.execute(
        select(Permission.permission_name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
        .order_by(Permission.permission_name)
    )
    return RoleOut(
        id=role.id,
        role_name=role.role_name,
        description=role.description,
        permissions=list(result.scalars().all()),
    )


async def ensure_super_admin(db: DBSessionDep, user: User) -> None:
    roles = await get_user_role_names(db, user.id)
    if SUPER_ADMIN_ROLE not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_DETAIL)


async def has_role_permission(db: DBSessionDep, user: User, permission_name: str) -> bool:
    roles = await get_user_role_names(db, user.id)
    if SUPER_ADMIN_ROLE in roles:
        return True
    permissions = await get_user_permissions(db, user.id)
    return permission_name in permissions


async def ensure_manage_roles(db: DBSessionDep, user: User) -> None:
    if not await has_role_permission(db, user, MANAGE_ROLES_PERMISSION):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_DETAIL)


async def apply_user_roles(db: DBSessionDep, user_id: int, role_ids: list[int]) -> None:
    await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for role_id in role_ids:
        role = await db.get(Role, role_id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role ID {role_id} not found",
            )
        db.add(UserRole(user_id=user_id, role_id=role_id))


async def apply_role_permissions(db: DBSessionDep, role_id: int, permission_ids: list[int]) -> None:
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for permission_id in permission_ids:
        perm = await db.get(Permission, permission_id)
        if perm is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission ID {permission_id} not found",
            )
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))


async def apply_user_permissions_direct(
    db: DBSessionDep, user_id: int, permission_ids: list[int], granted_by_id: int | None = None
) -> None:
    """
    Replace the old User Custom / Admin Custom role hack.
    Directly writes to user_permissions table.
    """
    await db.execute(delete(UserPermission).where(UserPermission.user_id == user_id))
    for permission_id in permission_ids:
        perm = await db.get(Permission, permission_id)
        if perm is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission ID {permission_id} not found",
            )
        db.add(UserPermission(
            user_id=user_id,
            permission_id=permission_id,
            granted_by_id=granted_by_id,
        ))


async def role_names_for_ids(db: DBSessionDep, role_ids: list[int]) -> list[str]:
    if not role_ids:
        return []
    result = await db.execute(select(Role.role_name).where(Role.id.in_(role_ids)))
    return list(result.scalars().all())


async def default_role_id(db: DBSessionDep, name: str) -> int | None:
    role = await db.scalar(select(Role).where(Role.role_name == name))
    return role.id if role else None


async def fetch_user_fresh(db: DBSessionDep, user_id: int) -> User:
    """Re-fetch user after commit to avoid MissingGreenlet on stale ORM state."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND_DETAIL)
    return user


async def fetch_role_fresh(db: DBSessionDep, role_id: int) -> Role:
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ROLE_NOT_FOUND_DETAIL)
    return role


async def resolve_role_ids_for_new_user(
    db: DBSessionDep,
    payload_role_ids: list[int] | None,
    current_user: User,
) -> list[int]:
    role_ids = payload_role_ids or []
    if not role_ids:
        default_id = await default_role_id(db, USER_ROLE)
        return [default_id] if default_id else []

    await ensure_manage_roles(db, current_user)
    if SUPER_ADMIN_ROLE in await role_names_for_ids(db, role_ids):
        await ensure_super_admin(db, current_user)
    return role_ids


async def apply_user_assignment_updates(
    db: DBSessionDep,
    user: User,
    payload: UserUpdateRequest,
    current_user: User,
) -> None:
    if payload.role_ids is None and payload.permission_ids is None:
        return

    await ensure_manage_roles(db, current_user)
    if payload.role_ids is not None:
        if SUPER_ADMIN_ROLE in await role_names_for_ids(db, payload.role_ids):
            await ensure_super_admin(db, current_user)
        await apply_user_roles(db, user.id, payload.role_ids)

    perm_ids = payload.permission_ids if payload.permission_ids is not None else []
    await apply_user_permissions_direct(db, user.id, perm_ids, granted_by_id=current_user.id)


async def apply_new_user_permissions(
    db: DBSessionDep,
    user_id: int,
    payload: UserCreateRequest,
    current_user: User,
) -> None:
    if not payload.permission_ids:
        return

    await ensure_manage_roles(db, current_user)
    await apply_user_permissions_direct(
        db, user_id, payload.permission_ids, granted_by_id=current_user.id
    )


# ---------------------------------------------------------------------------
# Me / Stats
# ---------------------------------------------------------------------------

@router.get("/me")
async def current_rbac_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> UserOut:
    return await serialize_user(db, current_user)


@router.get("/stats")
async def dashboard_stats(
    _current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> DashboardStats:
    total_users = await db.scalar(select(func.count(User.id))) or 0
    total_admins = await db.scalar(
        select(func.count(UserRole.user_id.distinct()))
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.role_name.in_([SUPER_ADMIN_ROLE, ADMIN_ROLE]))
    ) or 0
    return DashboardStats(
        total_users=total_users,
        total_admins=total_admins,
        active_sessions=1,
        reports_generated=0,
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    _: Annotated[User, Depends(require_permission("view_user"))],
    db: DBSessionDep,
) -> list[UserOut]:
    result = await db.execute(select(User).order_by(User.id.desc()))
    users = result.scalars().all()
    return [await serialize_user(db, u) for u in users]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    payload: UserCreateRequest,
    current_user: Annotated[User, Depends(require_permission("create_user"))],
    db: DBSessionDep,
) -> UserOut:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    email_lc = payload.email.lower()
    if await db.scalar(select(User).where(User.email == email_lc)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    username = (payload.username or email_lc).strip()
    if await db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    name_parts = payload.name.strip().split(maxsplit=1)
    user = User(
        username=username,
        slug=username.replace("@", "-at-").replace(".", "-"),
        email=email_lc,
        first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else "",
        password=hash_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(user)
    await db.flush()  # get user.id

    role_ids = await resolve_role_ids_for_new_user(db, payload.role_ids, current_user)
    await apply_user_roles(db, user.id, role_ids)
    await apply_new_user_permissions(db, user.id, payload, current_user)

    actor = full_name(current_user)
    log_audit_event(
        db, current_user, "Create User", USER_MANAGEMENT_AREA,
        f"{actor} created user '{user.first_name} {user.last_name}' ({email_lc})", request
    )
    await db.commit()

    # Re-fetch after commit to avoid MissingGreenlet
    user = await fetch_user_fresh(db, user.id)
    return await serialize_user(db, user)


@router.put("/users/{user_id}")
async def update_user(
    request: Request,
    user_id: int,
    payload: UserUpdateRequest,
    current_user: Annotated[User, Depends(require_permission("edit_user"))],
    db: DBSessionDep,
) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND_DETAIL)

    email_lc = payload.email.lower()
    if await db.scalar(select(User).where(User.email == email_lc, User.id != user_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    username = (payload.username or email_lc).strip()
    if await db.scalar(select(User).where(User.username == username, User.id != user_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    name_parts = payload.name.strip().split(maxsplit=1)
    user.email = email_lc
    user.username = username
    user.slug = username.replace("@", "-at-").replace(".", "-")
    user.first_name = name_parts[0]
    user.last_name = name_parts[1] if len(name_parts) > 1 else ""
    user.is_active = payload.is_active

    await apply_user_assignment_updates(db, user, payload, current_user)

    actor = full_name(current_user)
    log_audit_event(
        db, current_user, "Update User", USER_MANAGEMENT_AREA,
        f"{actor} updated user '{user.first_name} {user.last_name}' ({email_lc})", request
    )
    await db.commit()

    # Re-fetch after commit
    user = await fetch_user_fresh(db, user_id)
    return await serialize_user(db, user)


@router.delete("/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: Annotated[User, Depends(require_permission("delete_user"))],
    db: DBSessionDep,
) -> dict[str, str]:
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND_DETAIL)
    name = full_name(user)
    actor = full_name(current_user)
    await db.delete(user)
    log_audit_event(
        db, current_user, "Delete User", USER_MANAGEMENT_AREA,
        f"{actor} deleted user '{name}' ({user.email})", request
    )
    await db.commit()
    return {"message": "User deleted successfully"}


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

@router.get("/roles")
async def list_roles(
    _: Annotated[User, Depends(require_permission(MANAGE_ROLES_PERMISSION))],
    db: DBSessionDep,
) -> list[RoleOut]:
    result = await db.execute(select(Role).order_by(Role.id.asc()))
    roles = result.scalars().all()
    # Exclude auto-generated custom roles
    core_roles = [
        r for r in roles
        if not r.role_name.startswith("User Custom ")
        and not r.role_name.startswith("Admin Custom ")
    ]
    return [await serialize_role(db, role) for role in core_roles]


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    request: Request,
    payload: RoleCreateRequest,
    current_user: Annotated[User, Depends(require_permission(MANAGE_ROLES_PERMISSION))],
    db: DBSessionDep,
) -> RoleOut:
    role_name = payload.role_name.strip()
    if await db.scalar(select(Role).where(Role.role_name == role_name)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role already exists")
    role = Role(role_name=role_name, description=payload.description)
    db.add(role)
    await db.flush()
    await apply_role_permissions(db, role.id, payload.permission_ids)
    log_audit_event(
        db, current_user, "Create Role", ROLE_MANAGEMENT_AREA,
        f"{full_name(current_user)} created role '{role_name}'", request
    )
    await db.commit()
    refetched_role = await fetch_role_fresh(db, role.id)
    return await serialize_role(db, refetched_role)


@router.put("/roles/{role_id}")
async def update_role(
    request: Request,
    role_id: int,
    payload: RoleUpdateRequest,
    current_user: Annotated[User, Depends(require_permission(MANAGE_ROLES_PERMISSION))],
    db: DBSessionDep,
) -> RoleOut:
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ROLE_NOT_FOUND_DETAIL)
    role.description = payload.description
    await apply_role_permissions(db, role.id, payload.permission_ids)
    log_audit_event(
        db, current_user, "Update Role", ROLE_MANAGEMENT_AREA,
        f"{full_name(current_user)} updated role '{role.role_name}'", request
    )
    await db.commit()
    refetched_role = await fetch_role_fresh(db, role_id)
    return await serialize_role(db, refetched_role)


@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(
    request: Request,
    role_id: int,
    payload: PermissionUpdateRequest,
    current_user: Annotated[User, Depends(require_permission(MANAGE_ROLES_PERMISSION))],
    db: DBSessionDep,
) -> RoleOut:
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ROLE_NOT_FOUND_DETAIL)
    await apply_role_permissions(db, role.id, payload.permission_ids)
    log_audit_event(
        db, current_user, MODIFY_PERMISSIONS_ACTION, ROLE_MANAGEMENT_AREA,
        f"{full_name(current_user)} modified permissions for role '{role.role_name}'", request
    )
    await db.commit()
    refetched_role = await fetch_role_fresh(db, role_id)
    return await serialize_role(db, refetched_role)


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@router.get("/permissions")
async def list_permissions(
    _: Annotated[User, Depends(require_permission(MANAGE_ROLES_PERMISSION))],
    db: DBSessionDep,
) -> list[PermissionOut]:
    result = await db.execute(select(Permission).order_by(Permission.permission_name))
    return [
        PermissionOut(id=p.id, permission_name=p.permission_name, description=p.description)
        for p in result.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Admin-specific permission management
# ---------------------------------------------------------------------------

@router.put("/users/{user_id}/permissions")
async def set_user_direct_permissions(
    request: Request,
    user_id: int,
    payload: PermissionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> UserOut:
    await ensure_super_admin(db, current_user)
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND_DETAIL)

    await apply_user_permissions_direct(db, user_id, payload.permission_ids, granted_by_id=current_user.id)
    log_audit_event(
        db, current_user, MODIFY_PERMISSIONS_ACTION, ROLE_MANAGEMENT_AREA,
        f"{full_name(current_user)} set direct permissions for '{full_name(user)}'", request
    )
    await db.commit()
    user = await fetch_user_fresh(db, user_id)
    return await serialize_user(db, user)


# ---------------------------------------------------------------------------
# Admins (legacy endpoints kept for UI compatibility)
# ---------------------------------------------------------------------------

@router.get("/admins")
async def list_admins(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> list[UserOut]:
    await ensure_super_admin(db, current_user)
    result = await db.execute(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.role_name == ADMIN_ROLE)
        .distinct()
        .order_by(User.id.desc())
    )
    return [await serialize_user(db, u) for u in result.scalars().all()]


@router.post("/admins", status_code=status.HTTP_201_CREATED)
async def create_admin(
    request: Request,
    payload: UserCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> UserOut:
    await ensure_super_admin(db, current_user)
    admin_id = await default_role_id(db, ADMIN_ROLE)
    if admin_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin role not found")
    payload.role_ids = [admin_id]
    return await create_user(request, payload, current_user, db)


@router.put("/admins/{admin_id}/permissions")
async def update_admin_permissions(
    request: Request,
    admin_id: int,
    payload: PermissionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep,
) -> UserOut:
    await ensure_super_admin(db, current_user)
    admin = await db.get(User, admin_id)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    role_names = await get_user_role_names(db, admin.id)
    if ADMIN_ROLE not in role_names:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an admin")
    await apply_user_permissions_direct(db, admin_id, payload.permission_ids, granted_by_id=current_user.id)
    log_audit_event(
        db, current_user, MODIFY_PERMISSIONS_ACTION, ROLE_MANAGEMENT_AREA,
        f"{full_name(current_user)} updated permissions for admin '{full_name(admin)}'", request
    )
    await db.commit()
    admin = await fetch_user_fresh(db, admin_id)
    return await serialize_user(db, admin)


# ---------------------------------------------------------------------------
# Reports (legacy — now superseded by /api/reports/* endpoints)
# ---------------------------------------------------------------------------

@router.get("/reports")
async def reports(
    _: Annotated[User, Depends(require_permission("view_reports"))],
    db: DBSessionDep,
) -> dict[str, object]:
    from datetime import date

    from sqlalchemy import Date as SADate
    from sqlalchemy import cast

    from app.models.audit_log import AuditLog
    from app.models.blog import Blog

    today = date.today()
    total_users = await db.scalar(select(func.count(User.id))) or 0
    total_admins = await db.scalar(
        select(func.count(UserRole.user_id.distinct()))
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.role_name.in_([ADMIN_ROLE, SUPER_ADMIN_ROLE]))
    ) or 0
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    total_blogs = await db.scalar(select(func.count(Blog.id))) or 0
    published_blogs = await db.scalar(select(func.count(Blog.id)).where(Blog.status == "Published")) or 0
    blogs_today = await db.scalar(
        select(func.count(Blog.id)).where(cast(Blog.created_at, SADate) == today)
    ) or 0

    recent_logs = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
    )
    return {
        "summary": "Live RBAC report from PostgreSQL",
        "items": [
            {"name": "Total Users", "value": total_users},
            {"name": "Total Admins", "value": total_admins},
            {"name": "Active Users", "value": active_users},
            {"name": "Total Blogs", "value": total_blogs},
            {"name": "Published Blogs", "value": published_blogs},
            {"name": "Blogs Created Today", "value": blogs_today},
        ],
        "recent_activity": [
            {
                "name": log.action_type,
                "value": log.username,
                "description": log.description,
                "timestamp": log.created_at.isoformat(),
            }
            for log in recent_logs.scalars().all()
        ],
    }
