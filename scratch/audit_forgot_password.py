import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import DBSessionManager
from app.models.user import User


async def main() -> None:
    async with DBSessionManager.session() as db:
        result = await db.execute(
            select(User).where(User.email == "yazhinisg33@gmail.com")
        )
        user = result.scalar_one_or_none()
        print("user_found=", bool(user))
        if user:
            print("user_id=", user.id)
            print("token_hash_present=", bool(user.password_reset_token_hash))
            print("expires_at_present=", bool(user.password_reset_expires_at))
            print("expires_at=", user.password_reset_expires_at)


asyncio.run(main())
