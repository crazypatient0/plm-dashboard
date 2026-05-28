from datetime import datetime

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DocumentHistory(Base):
    __tablename__ = "document_history"
    __table_args__ = (
        UniqueConstraint("document_no", "doc_index", name="uq_document_history_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_no: Mapped[str] = mapped_column()
    doc_index: Mapped[str] = mapped_column()
    eai_message: Mapped[str | None] = mapped_column(Text, default=None)
    scraped_at: Mapped[datetime] = mapped_column()
    created_at: Mapped[datetime] = mapped_column()
