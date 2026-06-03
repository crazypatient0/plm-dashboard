from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PartHistory(Base):
    __tablename__ = "part_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_no: Mapped[str] = mapped_column()
    index_: Mapped[str] = mapped_column()
    share_status: Mapped[int | None] = mapped_column(default=None)
    sap_info: Mapped[str | None] = mapped_column(Text, default=None)
    scraped_at: Mapped[datetime] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()
