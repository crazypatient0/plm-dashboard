from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data_type: Mapped[str]
    status: Mapped[str]  # "success", "error", "partial"
    records_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None]
    started_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
