from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import (
    BLOG_STATUS_APPROVED,
    BLOG_STATUS_DRAFT,
    BLOG_STATUS_PENDING_REVIEW,
    BLOG_STATUS_PUBLISHED,
    BLOG_STATUS_REJECTED,
    CASCADE_ON_DELETE,
    USER_ID_FOREIGN_KEY,
)

from . import Base

SET_NULL_ON_DELETE = "SET NULL"

if TYPE_CHECKING:
    from app.models.user import User


class BlogCategory(Base):
    __tablename__ = "blog_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    blogs: Mapped[list["Blog"]] = relationship("Blog", back_populates="category")


class Blog(Base):
    __tablename__ = "blogs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    featured_image: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Creator
    author_id: Mapped[int] = mapped_column(
        ForeignKey(USER_ID_FOREIGN_KEY, ondelete=CASCADE_ON_DELETE), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("blog_categories.id", ondelete=SET_NULL_ON_DELETE), nullable=True
    )
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        Enum(
            BLOG_STATUS_DRAFT,
            BLOG_STATUS_PENDING_REVIEW,
            BLOG_STATUS_APPROVED,
            BLOG_STATUS_PUBLISHED,
            BLOG_STATUS_REJECTED,
            name="blog_status",
        ),
        nullable=False,
        server_default=BLOG_STATUS_DRAFT,
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Approver
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(USER_ID_FOREIGN_KEY, ondelete=SET_NULL_ON_DELETE), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Publisher
    published_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(USER_ID_FOREIGN_KEY, ondelete=SET_NULL_ON_DELETE), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], back_populates="blogs")
    approved_by: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by_id])
    published_by: Mapped["User | None"] = relationship("User", foreign_keys=[published_by_id])
    category: Mapped["BlogCategory | None"] = relationship("BlogCategory", back_populates="blogs")
