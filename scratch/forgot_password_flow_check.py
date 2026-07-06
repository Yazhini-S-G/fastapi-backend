import asyncio
import sys
from pathlib import Path

from fastapi import HTTPException, Request
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import DBSessionManager
from app.models.user import User
from app.router.auth import forgot_password
from app.schema.auth import ForgotPasswordRequest


def build_request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/auth/forgot-password", "headers": []})


EMAIL = "yazhinisg33@gmail.com"


async def token_state() -> tuple[bool, str | None]:
    async with DBSessionManager.session() as db:
        result = await db.execute(select(User).where(User.email == EMAIL))
        user = result.scalar_one_or_none()
        if user is None:
            return False, None
        return bool(user.password_reset_token_hash), (
            user.password_reset_expires_at.isoformat()
            if user.password_reset_expires_at
            else None
        )


async def run_flow() -> None:
    before_hash, before_expiry = await token_state()

    async with DBSessionManager.session() as db:
        try:
            result = await forgot_password(
                request=build_request(),
                payload=ForgotPasswordRequest(email=EMAIL),
                db=db,
            )
            print("status_code= 200")
            print("response=", result.model_dump())
        except HTTPException as exc:
            print("status_code=", exc.status_code)
            print("response=", {"detail": exc.detail})

    after_hash, after_expiry = await token_state()

    print("before_token_hash_present=", before_hash)
    print("before_expires_at=", before_expiry)
    print("after_token_hash_present=", after_hash)
    print("after_expires_at=", after_expiry)
    print("token_expiry_changed=", before_expiry != after_expiry)


asyncio.run(run_flow())
