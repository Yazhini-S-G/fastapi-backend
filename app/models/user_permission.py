from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import CASCADE_ON_DELETE, USER_ID_FOREIGN_KEY

from . import Base


class UserPermission(Base):
    """Direct user-to-permission grant — replaces the User Custom / Admin Custom role hack."""

    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", "permission_id", name="uq_user_permission"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(USER_ID_FOREIGN_KEY, ondelete=CASCADE_ON_DELETE), index=True
    )
    permission_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("permissions.id", ondelete=CASCADE_ON_DELETE), index=True
    )
    granted_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(USER_ID_FOREIGN_KEY, ondelete="SET NULL"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
