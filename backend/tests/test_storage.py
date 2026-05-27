"""Tests for the DataAccessLayer storage class."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.exceptions import PlmDataError
from src.models import Base, ScrapeLog, ScrapeRecord
from src.storage import DataAccessLayer


@pytest.fixture
def dal() -> DataAccessLayer:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = Session(engine)
    dal_instance = DataAccessLayer(session)
    yield dal_instance
    dal_instance.session.close()
    engine.dispose()


class TestSaveRecords:
    def test_inserts_correct_count(self, dal: DataAccessLayer) -> None:
        records = [{"part_no": "A"}, {"part_no": "B"}, {"part_no": "C"}]
        count = dal.save_records("parts", records)
        assert count == 3
        assert dal.get_records_count("parts") == 3

    def test_empty_list_returns_zero(self, dal: DataAccessLayer) -> None:
        count = dal.save_records("parts", [])
        assert count == 0

    def test_data_type_is_set(self, dal: DataAccessLayer) -> None:
        dal.save_records("parts", [{"part_no": "X"}])
        saved = dal.get_latest_records("parts", limit=1)
        assert saved[0].data_type == "parts"

    def test_deduplication_skips_duplicate(self, dal: DataAccessLayer) -> None:
        record = {"part_no": "ABC", "name": "Test Part"}
        first_count = dal.save_records("parts", [record])
        assert first_count == 1
        second_count = dal.save_records("parts", [record])
        assert second_count == 0
        assert dal.get_records_count("parts") == 1

    def test_deduplication_allows_different_data_type(self, dal: DataAccessLayer) -> None:
        record = {"part_no": "ABC"}
        dal.save_records("parts", [record])
        count = dal.save_records("documents", [record])
        assert count == 1

    def test_different_data_allows_insert(self, dal: DataAccessLayer) -> None:
        dal.save_records("parts", [{"part_no": "A"}])
        count = dal.save_records("parts", [{"part_no": "B"}])
        assert count == 1
        assert dal.get_records_count("parts") == 2


class TestGetLatestRecords:
    def test_returns_newest_first(self, dal: DataAccessLayer) -> None:
        dal.save_records("parts", [{"order": 1}])
        dal.save_records("parts", [{"order": 2}])
        dal.save_records("parts", [{"order": 3}])
        latest = dal.get_latest_records("parts", limit=3)
        assert len(latest) == 3
        assert latest[0].raw_data["order"] == 3
        assert latest[1].raw_data["order"] == 2
        assert latest[2].raw_data["order"] == 1

    def test_respects_limit(self, dal: DataAccessLayer) -> None:
        dal.save_records("parts", [{"n": i} for i in range(10)])
        latest = dal.get_latest_records("parts", limit=3)
        assert len(latest) == 3

    def test_empty_data_type(self, dal: DataAccessLayer) -> None:
        result = dal.get_latest_records("nonexistent")
        assert result == []


class TestGetRecordsByTimeRange:
    def test_returns_records_in_window(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        past = now - timedelta(hours=2)
        future = now + timedelta(hours=2)

        dal.session.add(ScrapeRecord(data_type="parts", raw_data={"test": True}, scraped_at=now))
        dal.session.commit()

        result = dal.get_records_by_time_range("parts", since=past, until=future)
        assert len(result) == 1

    def test_excludes_outside_window(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        old = now - timedelta(days=1)
        since = now - timedelta(hours=1)
        until = now + timedelta(hours=1)

        dal.session.add(ScrapeRecord(data_type="parts", raw_data={"old": True}, scraped_at=old))
        dal.session.commit()

        result = dal.get_records_by_time_range("parts", since=since, until=until)
        assert result == []

    def test_without_until(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        later = now + timedelta(hours=1)
        since = now - timedelta(hours=1)

        for dt in [now, later]:
            dal.session.add(ScrapeRecord(data_type="parts", raw_data={}, scraped_at=dt))
        dal.session.commit()

        result = dal.get_records_by_time_range("parts", since=since)
        assert len(result) == 2

    def test_empty_data_type(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        result = dal.get_records_by_time_range("nonexistent", since=now - timedelta(days=1))
        assert result == []


class TestGetSummary:
    def test_returns_correct_stats(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        for i in range(3):
            dal.session.add(
                ScrapeRecord(
                    data_type="parts",
                    raw_data={"i": i},
                    scraped_at=now - timedelta(hours=i),
                )
            )
        dal.session.commit()

        summary = dal.get_summary("parts")
        assert summary["total"] == 3
        assert summary["latest_scraped_at"] is not None
        assert summary["oldest_scraped_at"] is not None
        assert summary["latest_scraped_at"] > summary["oldest_scraped_at"]

    def test_empty_data_type(self, dal: DataAccessLayer) -> None:
        summary = dal.get_summary("nonexistent")
        assert summary["total"] == 0
        assert summary["latest_scraped_at"] is None
        assert summary["oldest_scraped_at"] is None


class TestPruneOldData:
    def test_deletes_old_records_only(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        old = now - timedelta(days=60)
        recent = now - timedelta(days=5)

        dal.session.add(ScrapeRecord(data_type="parts", raw_data={"old": True}, scraped_at=old))
        dal.session.add(
            ScrapeRecord(data_type="parts", raw_data={"recent": True}, scraped_at=recent)
        )
        dal.session.commit()

        deleted = dal.prune_old_data(retention_days=30)
        assert deleted == 1

        remaining = dal.get_records_count("parts")
        assert remaining == 1

    def test_no_records_to_delete(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        dal.session.add(ScrapeRecord(data_type="parts", raw_data={}, scraped_at=now))
        dal.session.commit()

        deleted = dal.prune_old_data(retention_days=30)
        assert deleted == 0

    def test_empty_database(self, dal: DataAccessLayer) -> None:
        deleted = dal.prune_old_data(retention_days=30)
        assert deleted == 0


class TestPruneOldLogs:
    def test_deletes_old_logs(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        old = now - timedelta(days=60)
        recent = now - timedelta(days=5)

        dal.session.add(ScrapeLog(data_type="parts", status="success", started_at=old))
        dal.session.add(ScrapeLog(data_type="parts", status="success", started_at=recent))
        dal.session.commit()

        deleted = dal.prune_old_logs(retention_days=30)
        assert deleted == 1

    def test_empty_database(self, dal: DataAccessLayer) -> None:
        deleted = dal.prune_old_logs(retention_days=30)
        assert deleted == 0


class TestSearchRecords:
    def test_matches_field_value(self, dal: DataAccessLayer) -> None:
        dal.save_records(
            "parts",
            [
                {"part_no": "ABC-123", "name": "Bolt"},
                {"part_no": "DEF-456", "name": "Nut"},
                {"part_no": "GHI-789", "name": "Screw"},
            ],
        )
        result = dal.search_records("parts", "part_no", "ABC")
        assert len(result) == 1
        assert result[0].raw_data["part_no"] == "ABC-123"

    def test_case_insensitive_match(self, dal: DataAccessLayer) -> None:
        dal.save_records("parts", [{"name": "Aluminum Bracket"}])
        result = dal.search_records("parts", "name", "aluminum")
        assert len(result) == 1

    def test_no_match(self, dal: DataAccessLayer) -> None:
        dal.save_records("parts", [{"name": "Bolt"}])
        result = dal.search_records("parts", "name", "Zebra")
        assert result == []

    def test_empty_database(self, dal: DataAccessLayer) -> None:
        result = dal.search_records("parts", "name", "anything")
        assert result == []


class TestGetRecentLogs:
    def test_returns_newest_first(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        for i in range(3):
            dal.session.add(
                ScrapeLog(
                    data_type="parts",
                    status="success",
                    started_at=now - timedelta(hours=i),
                )
            )
        dal.session.commit()

        logs = dal.get_recent_logs(limit=3)
        assert len(logs) == 3
        assert logs[0].started_at > logs[1].started_at

    def test_respects_data_type_filter(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        dal.session.add(ScrapeLog(data_type="parts", status="success", started_at=now))
        dal.session.add(ScrapeLog(data_type="documents", status="success", started_at=now))
        dal.session.commit()

        logs = dal.get_recent_logs(data_type="parts")
        assert len(logs) == 1
        assert logs[0].data_type == "parts"

    def test_empty_database(self, dal: DataAccessLayer) -> None:
        logs = dal.get_recent_logs()
        assert logs == []


class TestSaveLog:
    def test_saves_and_persists_log(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        log = ScrapeLog(
            data_type="parts",
            status="success",
            records_count=10,
            started_at=now,
            completed_at=now,
        )
        dal.save_log(log)
        assert log.id is not None
        assert log.id > 0

        fetched = dal.session.get(ScrapeLog, log.id)
        assert fetched is not None
        assert fetched.status == "success"
        assert fetched.records_count == 10

    def test_saves_error_log(self, dal: DataAccessLayer) -> None:
        now = datetime.now(UTC)
        log = ScrapeLog(
            data_type="documents",
            status="error",
            error_message="Connection timeout",
            started_at=now,
        )
        dal.save_log(log)
        assert log.error_message == "Connection timeout"


class TestGetRecordsCount:
    def test_returns_correct_count(self, dal: DataAccessLayer) -> None:
        dal.save_records("parts", [{"i": i} for i in range(5)])
        assert dal.get_records_count("parts") == 5

    def test_empty_data_type(self, dal: DataAccessLayer) -> None:
        assert dal.get_records_count("nonexistent") == 0

    def test_multiple_data_types(self, dal: DataAccessLayer) -> None:
        dal.save_records("parts", [{"i": i} for i in range(3)])
        dal.save_records("documents", [{"i": i} for i in range(7)])
        assert dal.get_records_count("parts") == 3
        assert dal.get_records_count("documents") == 7


class TestErrorHandling:
    def test_raises_plm_data_error_on_db_failure(
        self, dal: DataAccessLayer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _broken_execute(*args: object, **kwargs: object) -> object:
            msg = "database is corrupted"
            raise RuntimeError(msg)

        monkeypatch.setattr(dal.session, "execute", _broken_execute)
        with pytest.raises(PlmDataError):
            dal.get_latest_records("parts")
