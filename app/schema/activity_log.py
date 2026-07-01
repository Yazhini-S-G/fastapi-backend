from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    username: str
    email: str | None = None
    module: str
    action_type: str
    description: str
    ip_address: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityLogsPaginated(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    size: int
    pages: int


class AdminSessionOut(BaseModel):
    admin_name: str
    admin_email: str | None = None
    login_time: datetime
    logout_time: datetime | None = None
    session_duration: str | None = None
    ip_address: str | None = None
    is_active: bool = False


class AdminSessionPaginated(BaseModel):
    items: list[AdminSessionOut]
    total: int
    page: int
    size: int
    pages: int


class ActivityStats(BaseModel):
    # Auth
    total_logins_today: int = 0
    failed_logins_today: int = 0
    total_active_sessions: int = 0

    # Blog
    blogs_created_today: int = 0
    blogs_edited_today: int = 0
    blogs_deleted_today: int = 0
    blogs_published_today: int = 0
    blogs_approved_today: int = 0

    # User / Role Management
    user_management_actions: int = 0
    role_permission_changes: int = 0

    # Chart data
    activity_chart_data: list[dict[str, object]] | None = None
