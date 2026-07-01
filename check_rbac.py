import asyncio

from sqlalchemy import select

from app.core.database import DBSessionManager
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User


async def check() -> None:
    async with DBSessionManager.session() as db:
        user = await db.scalar(select(User).where(User.email == "yazhini33@gmail.com"))
        if not user:
            print("User not found!")
            return
        print(f"User ID: {user.id}")

        roles = await db.execute(
            select(Role.role_name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
        print(f"Roles: {roles.scalars().all()}")

        perms = await db.execute(
            select(Permission.permission_name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user.id)
            .distinct()
        )
        print(f"Permissions: {perms.scalars().all()}")


if __name__ == "__main__":
    asyncio.run(check())
