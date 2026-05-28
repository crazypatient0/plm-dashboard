from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ConversionCurrent(Base, TimestampMixin):
    __tablename__ = "conversion_current"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column()
    state: Mapped[str | None] = mapped_column(Text, default=None)
    target_format: Mapped[str | None] = mapped_column(Text, default=None)
    created_utc: Mapped[str | None] = mapped_column(Text, default=None)
    started_utc: Mapped[str | None] = mapped_column(Text, default=None)
    scraped_at: Mapped[datetime] = mapped_column()
