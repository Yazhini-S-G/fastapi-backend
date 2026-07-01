import asyncio

from sqlalchemy import select

from app.core.database import DBSessionManager, engine
from app.core.manager import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from app.core.security import hash_password
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User


async def fix_rbac() -> None:
    # Make sure tables are created
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with DBSessionManager.session() as db:
        # 1. Ensure permissions exist
        permissions = {}
        for perm_name in DEFAULT_PERMISSIONS:
            perm_result = await db.execute(select(Permission).where(Permission.permission_name == perm_name))
            perm = perm_result.scalar_one_or_none()
            if not perm:
                perm = Permission(permission_name=perm_name, description=perm_name.replace("_", " ").title())
                db.add(perm)
                await db.flush()
            permissions[perm_name] = perm

        # 2. Ensure roles exist
        roles = {}
        for role_name in DEFAULT_ROLES:
            role_result = await db.execute(select(Role).where(Role.role_name == role_name))
            role = role_result.scalar_one_or_none()
            if not role:
                role = Role(role_name=role_name, description=f"{role_name} role")
                db.add(role)
                await db.flush()
            roles[role_name] = role

        # 3. Ensure Super Admin has all permissions
        super_admin_role = roles["Super Admin"]
        for perm_name in DEFAULT_PERMISSIONS:
            perm = permissions[perm_name]
            role_perm_result = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == super_admin_role.id,
                    RolePermission.permission_id == perm.id
                )
            )
            if not role_perm_result.scalar_one_or_none():
                db.add(RolePermission(role_id=super_admin_role.id, permission_id=perm.id))

        # Also ensure Admin has view_user
        admin_role = roles["Admin"]
        perm = permissions["view_user"]
        admin_perm_result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == admin_role.id,
                RolePermission.permission_id == perm.id
            )
        )
        if not admin_perm_result.scalar_one_or_none():
            db.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

        # 4. Ensure yazhini33@gmail.com exists and is a Super Admin
        email = "yazhini33@gmail.com"
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()

        if not user:
            user = User(
                username=email,
                slug="yazhini33-at-gmail-com",
                email=email,
                first_name="Yazhini",
                last_name="",
                password=hash_password("password123"),  # Default password if we have to create
                is_active=True
            )
            db.add(user)
            await db.flush()

        # 5. Assign Super Admin role to the user
        user_role_result = await db.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == super_admin_role.id
            )
        )
        if not user_role_result.scalar_one_or_none():
            # Delete any other roles first to be safe
            from sqlalchemy import delete
            await db.execute(delete(UserRole).where(UserRole.user_id == user.id))
            db.add(UserRole(user_id=user.id, role_id=super_admin_role.id))

        await db.commit()
        print(f"RBAC fixed successfully. User {email} has Super Admin role.")


if __name__ == "__main__":
    asyncio.run(fix_rbac())
