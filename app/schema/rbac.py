from pydantic import BaseModel, EmailStr, Field


class PermissionOut(BaseModel):
    id: int
    permission_name: str
    description: str = ""


class RoleOut(BaseModel):
    id: int
    role_name: str
    description: str = ""
    permissions: list[str] = []


class UserOut(BaseModel):
    id: int
    name: str
    username: str
    email: EmailStr
    is_active: bool
    roles: list[str]
    permissions: list[str]


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    username: str | None = Field(default=None, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)
    role_ids: list[int] | None = None
    permission_ids: list[int] | None = None
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    username: str | None = Field(default=None, max_length=100)
    email: EmailStr
    is_active: bool = True
    role_ids: list[int] | None = None
    permission_ids: list[int] | None = None


class RoleCreateRequest(BaseModel):
    role_name: str = Field(min_length=1, max_length=100)
    description: str = ""
    permission_ids: list[int] = []


class RoleUpdateRequest(BaseModel):
    description: str = ""
    permission_ids: list[int] = []


class PermissionUpdateRequest(BaseModel):
    permission_ids: list[int] = []


class DashboardStats(BaseModel):
    total_users: int
    total_admins: int
    active_sessions: int
    reports_generated: int
