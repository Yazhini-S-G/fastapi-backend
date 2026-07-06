from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import USER_ID_FOREIGN_KEY

from . import Base


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey(USER_ID_FOREIGN_KEY))

    address_line1: Mapped[str]
    address_line2: Mapped[str]
    city: Mapped[str]
    state: Mapped[str]
    country: Mapped[str]
    postal_code: Mapped[str]

    is_default: Mapped[bool]
