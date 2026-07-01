from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id")
    )

    address_line1: Mapped[str]
    address_line2: Mapped[str]
    city: Mapped[str]
    state: Mapped[str]
    country: Mapped[str]
    postal_code: Mapped[str]

    is_default: Mapped[bool]
