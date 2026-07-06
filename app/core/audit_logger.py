from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import DetachedInstanceError

from app.models.audit_log import AuditLog
from app.models.user import User


def _resolve_user_context(user: User, fallback_email: str | None) -> tuple[str, int | None, str | None]:
    try:
        first = getattr(user, "first_name", "") or ""
        last = getattr(user, "last_name", "") or ""
        username = f"{first} {last}".strip() or getattr(user, "email", "Unknown")
        user_id = getattr(user, "id", None)
        resolved_email = fallback_email or getattr(user, "email", None)
    except (AttributeError, DetachedInstanceError):
        return "System", None, fallback_email
    return username, user_id, resolved_email


def log_audit_event(
    db: AsyncSession,
    user: User | None,  # User model or None
    action_type: str,
    module: str,
    description: str,
    request: Request | None = None,
    email: str | None = None,
    status: str = "Success",
) -> None:
    ip_address = None
    if request:
        client = request.client
        if client is not None:
            ip_address = client.host

    username = "System"
    user_id = None
    resolved_email = email

    if user is not None:
        username, user_id, resolved_email = _resolve_user_context(user, resolved_email)
    elif email:
        username = email

    audit_log = AuditLog(
        user_id=user_id,
        username=username,
        email=resolved_email,
        module=module,
        action_type=action_type,
        description=description,
        ip_address=ip_address,
        status=status,
    )

    db.add(audit_log)
    # Caller is responsible for committing the session
