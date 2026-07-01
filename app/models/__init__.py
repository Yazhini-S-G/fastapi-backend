# ruff: noqa: E402
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Export models in proper dependency order
from .address import Address as Address
from .audit_log import AuditLog as AuditLog
from .blog import Blog as Blog
from .blog import BlogCategory as BlogCategory
from .category import Category as Category
from .role import Permission as Permission
from .role import Role as Role
from .role import RolePermission as RolePermission
from .role import UserRole as UserRole
from .user import User as User
from .user_permission import UserPermission as UserPermission
