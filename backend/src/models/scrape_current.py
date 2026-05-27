from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from .base import Base, TimestampMixin

BJ_TZ = ZoneInfo("Asia/Shanghai")


class _JsonText(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any | None, dialect: Any) -> str | None:
        import json

        return json.dumps(value) if value is not None else None

    def process_result_value(self, value: str | None, dialect: Any) -> Any | None:
        import json

        return json.loads(value) if value is not None else None


JSON_DICT = _JsonText


class ScrapeCurrent(TimestampMixin, Base):
    __tablename__ = "scrape_current"
    __table_args__ = (
        UniqueConstraint("data_type", "item_key", "item_index", name="uq_current_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data_type: Mapped[str]
    item_key: Mapped[str]
    item_index: Mapped[str | None]
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON_DICT)
    scraped_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(BJ_TZ)
    )
