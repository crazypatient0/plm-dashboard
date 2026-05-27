from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

BJ_TZ = ZoneInfo("Asia/Shanghai")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(BJ_TZ)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None, onupdate=lambda: datetime.now(BJ_TZ)
    )
