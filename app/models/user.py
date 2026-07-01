from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base

if TYPE_CHECKING:
    from app.models.blog import Blog
    from app.models.role import Role


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    username: Mapped[str] = mapped_column(index=True, unique=True)
    slug: Mapped[str] = mapped_column(index=True, unique=True)
    email: Mapped[str] = mapped_column(index=True, unique=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    password: Mapped[str]
    password_reset_token_hash: Mapped[str | None] = mapped_column(
        String, index=True, unique=True, nullable=True
    )
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users"
    )

    # Only link author_id → avoids ambiguity with approved_by_id / published_by_id
    blogs: Mapped[list["Blog"]] = relationship(
        "Blog",
        foreign_keys="Blog.author_id",
        back_populates="author",
        cascade="all, delete-orphan"
    )
