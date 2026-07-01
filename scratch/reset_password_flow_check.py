import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import DBSessionManager
from app.core.security import generate_password_reset_token, hash_password
from app.models.user import User
from app.router.auth import login_user, reset_password
from app.schema.auth import LoginRequest, ResetPasswordRequest


async def main() -> None:
    email = "codex-reset-flow@example.com"
    old_password = "OldPassword123!"
    new_password = "NewPassword123!"

    async with DBSessionManager.session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                username=email,
                slug="codex-reset-flow-example-com",
                email=email,
                first_name="Codex",
                last_name="ResetFlow",
                password=hash_password(old_password),
            )
            db.add(user)
            await db.flush()

        token, token_hash, expires_at = generate_password_reset_token()
        user.password_reset_token_hash = token_hash
        user.password_reset_expires_at = expires_at
        await db.commit()

    async with DBSessionManager.session() as db:
        response = await reset_password(
            request=None,  # type: ignore
            payload=ResetPasswordRequest(
                reset_token=token,
                new_password=new_password,
                confirm_password=new_password,
            ),
            db=db,
        )
        print("reset_message=", response.message)

    async with DBSessionManager.session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        print("token_hash_removed=", user.password_reset_token_hash is None)
        print("expires_at_removed=", user.password_reset_expires_at is None)

    async with DBSessionManager.session() as db:
        tokens = await login_user(
            request=None,  # type: ignore
            payload=LoginRequest(email=email, password=new_password),
            db=db,
        )
        print("login_with_new_password=", bool(tokens.get("access_token")))


asyncio.run(main())
