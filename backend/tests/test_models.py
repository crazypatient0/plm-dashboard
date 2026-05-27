"""Tests for SQLAlchemy model definitions."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.models import Base, ScrapeLog, ScrapeRecord
from src.models.base import TimestampMixin


@pytest.fixture
def in_memory_db() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


class TestScrapeRecord:
    def test_create_record(self, in_memory_db: Session) -> None:
        record = ScrapeRecord(
            data_type="parts",
            raw_data={"rows": [{"part_no": "ABC"}]},
        )
        in_memory_db.add(record)
        in_memory_db.commit()

        assert record.id is not None
        assert record.id > 0
        assert record.data_type == "parts"
        assert record.raw_data == {"rows": [{"part_no": "ABC"}]}
        assert isinstance(record.scraped_at, datetime)
        assert isinstance(record.created_at, datetime)

    def test_has_timestamps(self, in_memory_db: Session) -> None:
        """ScrapeRecord inherits TimestampMixin -> has created_at/updated_at."""
        assert issubclass(ScrapeRecord, TimestampMixin)
        record = ScrapeRecord(
            data_type="documents",
            raw_data={},
        )
        in_memory_db.add(record)
        in_memory_db.commit()

        assert record.created_at is not None
        # updated_at is None until update
        assert record.updated_at is None

    def test_raw_data_stored_as_json(self, in_memory_db: Session) -> None:
        """raw_data is a dict at Python level, stored as Text/JSON in DB."""
        payload = {"items": [1, 2, 3], "meta": {"count": 3}}
        record = ScrapeRecord(data_type="conversion", raw_data=payload)
        in_memory_db.add(record)
        in_memory_db.commit()

        # Read raw from DB to verify JSON serialization
        raw = in_memory_db.execute(
            text("SELECT raw_data FROM scrape_records WHERE id = :id"),
            {"id": record.id},
        ).scalar_one()
        assert json.loads(raw) == payload


class TestScrapeLog:
    def test_create_log(self, in_memory_db: Session) -> None:
        log = ScrapeLog(
            data_type="parts",
            status="success",
            records_count=5,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        in_memory_db.add(log)
        in_memory_db.commit()

        assert log.id is not None
        assert log.id > 0
        assert log.data_type == "parts"
        assert log.status == "success"
        assert log.records_count == 5
        assert log.error_message is None

    def test_log_error_status(self, in_memory_db: Session) -> None:
        log = ScrapeLog(
            data_type="documents",
            status="error",
            records_count=0,
            error_message="Connection timeout",
            started_at=datetime.now(UTC),
        )
        in_memory_db.add(log)
        in_memory_db.commit()

        assert log.status == "error"
        assert log.error_message == "Connection timeout"
        assert log.completed_at is None

    def test_log_default_records_count(self, in_memory_db: Session) -> None:
        log = ScrapeLog(
            data_type="parts",
            status="success",
            started_at=datetime.now(UTC),
        )
        in_memory_db.add(log)
        in_memory_db.commit()
        assert log.records_count == 0

    def test_log_requires_started_at(self, in_memory_db: Session) -> None:
        """started_at is not nullable so omitting it should fail."""
        log = ScrapeLog(
            data_type="parts",
            status="error",
        )
        in_memory_db.add(log)
        with pytest.raises(Exception):
            in_memory_db.commit()
