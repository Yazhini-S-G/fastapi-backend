from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.audit_logger import log_audit_event
from app.core.database import DBSessionDep
from app.core.email import send_password_reset_email
from app.core.jwt import create_access_token, create_refresh_token, verify_token
from app.core.rbac import get_user_role_names
from app.core.security import (
    generate_password_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
    verify_password_reset_token,
)
from app.core.token_blacklist import blacklist_token, is_token_blacklisted
from app.models.role import Role, UserRole
from app.models.user import User
from app.schema.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ProfileResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
)

INVALID_TOKEN = "Invalid token"
PASSWORDS_DO_NOT_MATCH = "Passwords do not match"
INVALID_REFRESH_TOKEN = "Invalid refresh token"
INVALID_RESET_TOKEN = "Invalid reset token"

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: DBSessionDep
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN,
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not isinstance(user_id, (str, int)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN,
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN,
            headers={"WWW-Authenticate": "Bearer"}
        ) from None

    result = await db.execute(
        select(User).where(User.id == user_id_int)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


@router.post("/register")
async def register_user(
    payload: RegisterRequest,
    db: DBSessionDep
) -> dict[str, str | int]:
    email_identity = payload.email.lower()

    # Password validation
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=PASSWORDS_DO_NOT_MATCH
        )

    # Email uniqueness check
    result = await db.execute(
        select(User).where(User.email == email_identity)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    name_parts = payload.name.strip().split(maxsplit=1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Create user
    new_user = User(
        username=email_identity,
        slug=email_identity.replace("@", "-at-").replace(".", "-"),
        email=email_identity,
        first_name=first_name,
        last_name=last_name,
        password=hash_password(payload.password)
    )

    db.add(new_user)
    await db.flush()

    user_count = await db.scalar(select(User.id).order_by(User.id.asc()).limit(1))
    role_name = "Super Admin" if user_count == new_user.id else "User"
    default_role = await db.scalar(select(Role).where(Role.role_name == role_name))
    if default_role is not None:
        db.add(UserRole(user_id=new_user.id, role_id=default_role.id))

    await db.commit()
    await db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id
    }


@router.post("/login")
async def login_user(
    request: Request,
    payload: LoginRequest,
    db: DBSessionDep
) -> dict[str, str]:
    email_identity = payload.email.lower()

    result = await db.execute(
        select(User).where(User.email == email_identity)
    )
    user = result.scalar_one_or_none()

    if user is None:
        log_audit_event(
            db, None, "Failed Login", "Auth",
            f"Failed login attempt for {email_identity}",
            request, email=email_identity, status="Failed"
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email"
        )

    if not verify_password(payload.password, user.password):
        log_audit_event(
            db, user, "Failed Login", "Auth",
            f"Failed login attempt for {email_identity}",
            request, status="Failed"
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )

    token_data = {
        "sub": str(user.id),
        "email": user.email
    }

    log_audit_event(db, user, "Login", "Auth", f"User {user.first_name} logged in", request)
    await db.commit()

    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep
) -> dict[str, str]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    blacklist_token(credentials.credentials)
    log_audit_event(
        db, current_user, "Logout", "Auth",
        f"User {current_user.first_name} logged out", request
    )
    await db.commit()

    return {
        "message": "Logged out successfully"
    }


@router.post("/refresh-token")
async def refresh_token(
    payload: RefreshTokenRequest,
    db: DBSessionDep
) -> RefreshTokenResponse:
    token_payload = verify_token(payload.refresh_token)

    if token_payload is None or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_REFRESH_TOKEN
        )

    user_id = token_payload.get("sub")
    if not isinstance(user_id, (str, int)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_REFRESH_TOKEN
        )

    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_REFRESH_TOKEN
        ) from None

    result = await db.execute(
        select(User).where(User.id == user_id_int)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_REFRESH_TOKEN
        )

    token_data = {
        "sub": str(user.id),
        "email": user.email
    }

    return RefreshTokenResponse(
        **{
            "access_token": create_access_token(token_data),
            "token_type": "bearer"
        }
    )


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: DBSessionDep
) -> ForgotPasswordResponse:
    email_identity = payload.email.lower()

    logger.info(f"Forgot password request received for email: {email_identity}")

    result = await db.execute(
        select(User).where(User.email == email_identity).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    # Always return success message to prevent email enumeration
    success_msg = "Reset link sent."

    if user is None:
        logger.warning(f"Forgot password email not found: {email_identity}")
        # Simulate some delay to prevent timing attacks, then return
        import asyncio
        await asyncio.sleep(0.5)
        return ForgotPasswordResponse(message=success_msg)

    logger.info(f"Forgot password email found: {user.email}")
    reset_token, reset_token_hash, expires_at = generate_password_reset_token()
    logger.info(f"Forgot password token generated for {user.email}")

    user.password_reset_token_hash = reset_token_hash
    user.password_reset_expires_at = expires_at

    # Flush to database without committing to avoid detaching the object
    await db.flush()
    logger.info(f"Forgot password token saved for {user.email}")

    # Send email
    email_result = await send_password_reset_email(user.email, reset_token)
    if email_result.sent:
        logger.info(f"Forgot password email sent to {user.email}")
    else:
        logger.error(f"Forgot password email sending failed for {user.email}: {email_result.error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email sending failed: {email_result.error}"
        )

    log_audit_event(
        db, user, "Password Reset Requested", "Auth",
        f"Password reset requested for {user.email}", request
    )
    await db.commit()
    logger.info("Database committed. Forgot-password request complete.")

    return ForgotPasswordResponse(message=success_msg)


@router.post("/reset-password")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: DBSessionDep
) -> ResetPasswordResponse:
    reset_token_hash = hash_reset_token(payload.reset_token)

    result = await db.execute(
        select(User).where(User.password_reset_token_hash == reset_token_hash)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN
        )

    expires_at = user.password_reset_expires_at
    if expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN
        )

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )

    if not verify_password_reset_token(
        payload.reset_token,
        user.password_reset_token_hash,
        user.password_reset_expires_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN
        )

    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=PASSWORDS_DO_NOT_MATCH
        )

    user.password = hash_password(payload.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None

    log_audit_event(db, user, "Password Reset", "Auth", f"{user.email} reset their password", request)
    await db.commit()

    return ResetPasswordResponse(
        message="Password reset successfully"
    )


@router.post("/change-password")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep
) -> ChangePasswordResponse:
    if not verify_password(payload.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )

    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=PASSWORDS_DO_NOT_MATCH
        )

    current_user.password = hash_password(payload.new_password)

    log_audit_event(
        db, current_user, "Password Changed", "Auth",
        f"{current_user.email} changed their password", request
    )
    await db.commit()

    return ChangePasswordResponse(
        message="Password changed successfully"
    )


@router.get("/profile")
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSessionDep
) -> ProfileResponse:
    full_name = f"{current_user.first_name} {current_user.last_name}".strip()
    roles = await get_user_role_names(db, current_user.id)

    return ProfileResponse(
        id=current_user.id,
        name=full_name,
        email=current_user.email,
        role=", ".join(roles),
        account_status="Active" if current_user.is_active else "Inactive",
    )
