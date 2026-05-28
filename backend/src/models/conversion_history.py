from datetime import datetime

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ConversionHistory(Base):
    __tablename__ = "conversion_history"
    __table_args__ = (
        UniqueConstraint("source", name="uq_conversion_history_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(unique=True)
    state: Mapped[str | None] = mapped_column(Text, default=None)
    target_format: Mapped[str | None] = mapped_column(Text, default=None)
    created_utc: Mapped[str | None] = mapped_column(Text, default=None)
    started_utc: Mapped[str | None] = mapped_column(Text, default=None)
    scraped_at: Mapped[datetime] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()
