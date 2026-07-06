from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    username: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    module: Mapped[str] = mapped_column(String, index=True)
    action_type: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, index=True, default="Success")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
