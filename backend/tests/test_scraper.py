"""Tests for the PLM data scraper service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.exceptions import PlmAuthError, PlmConnectionError
from src.models import Base, ScrapeLog, ScrapeRecord
from src.plm_client import PlmClient
from src.scraper import (
    MQ_ACS_COLUMNS,
    PARTS_COLUMNS,
    Scraper,
    ScrapeResult,
    _extract_columns,
    _filter_conversion,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock(spec=PlmClient)


@pytest.fixture
def scraper(
    mock_client: MagicMock, in_memory_db: Session
) -> Scraper:
    return Scraper(client=mock_client, db=in_memory_db)


# ---------------------------------------------------------------------------
# Column extraction
# ---------------------------------------------------------------------------

class TestExtractColumns:
    def test_extract_parts_columns(self) -> None:
        row = {
            "columns": [
                None, None, None, None, None, None,
                "PART-001",  # col 6 = part_no
                "A",         # col 7 = index
                None, None, None, None, None,
                9,           # col 13 = share_status
            ] + [None] * 48 + [
                "OK"         # col 62 = sap_info
            ]
        }
        result = _extract_columns(row, PARTS_COLUMNS)
        assert result["part_no"] == "PART-001"
        assert result["index"] == "A"
        assert result["share_status"] == 9
        assert result["sap_info"] == "OK"

    def test_extract_documents_columns(self) -> None:
        row = {
            "columns": [
                None, None, None,
                "DOC-100",   # col 3
                "B",         # col 4
            ] + [None] * 30 + [
                "Sent",      # col 35
            ]
        }
        from src.scraper import DOCUMENTS_COLUMNS
        result = _extract_columns(row, DOCUMENTS_COLUMNS)
        assert result["document_no"] == "DOC-100"
        assert result["doc_index"] == "B"
        assert result["eai_message"] == "Sent"

    def test_extract_conversion_columns(self) -> None:
        row = {
            "columns": [
                None,
                "waiting",       # col 1
                None, None,
                "step_ap214",   # col 4
                "2026-05-25T01:00:00Z",  # col 5
                "2026-05-25T01:05:00Z",  # col 6
            ]
        }
        result = _extract_columns(row, MQ_ACS_COLUMNS)
        assert result["state"] == "waiting"
        assert result["target_format"] == "step_ap214"
        assert result["created_utc"] == "2026-05-25T01:00:00Z"
        assert result["started_utc"] == "2026-05-25T01:05:00Z"

    def test_short_columns_list_defaults_to_none(self) -> None:
        row = {"columns": ["a", "b"]}
        result = _extract_columns(row, PARTS_COLUMNS)
        assert result["part_no"] is None
        assert result["sap_info"] is None

    def test_missing_columns_key_defaults_to_none(self) -> None:
        result = _extract_columns({}, PARTS_COLUMNS)
        assert result["part_no"] is None


# ---------------------------------------------------------------------------
# MQ ACS filtering
# ---------------------------------------------------------------------------

class TestFilterMqAcs:
    def test_filters_to_step_ap214_only(self) -> None:
        records = [
            {"target_format": "step_ap214"},
            {"target_format": "step_203"},
            {"target_format": "step_ap214"},
        ]
        filtered = _filter_conversion(records)
        assert len(filtered) == 2
        assert all(r["target_format"] == "step_ap214" for r in filtered)

    def test_empty_list(self) -> None:
        assert _filter_conversion([]) == []

    def test_no_match(self) -> None:
        records = [{"target_format": "step_203"}, {"target_format": "step_214"}]
        assert _filter_conversion(records) == []


# ---------------------------------------------------------------------------
# Scraper — query mocks
# ---------------------------------------------------------------------------

def _make_part_row(part_no: str, status: int = 9) -> dict:
    cols: list = [None] * 78
    cols[6] = part_no
    cols[7] = "A"
    cols[13] = status
    cols[62] = "OK"
    return {"columns": cols}


def _make_doc_row(doc_no: str, eai: str = "Sent") -> dict:
    cols: list = [None] * 39
    cols[3] = doc_no
    cols[4] = "A"
    cols[35] = eai
    return {"columns": cols}


def _make_mq_row(target: str = "step_ap214") -> dict:
    cols: list = [None] * 13
    cols[1] = "waiting"
    cols[4] = target
    cols[5] = "2026-05-25T01:00:00Z"
    cols[6] = "2026-05-25T01:05:00Z"
    return {"columns": cols}


class TestScraperQuery:
    def test_scrape_parts(self, scraper: Scraper, mock_client: MagicMock) -> None:
        mock_client.search_parts.return_value = [
            _make_part_row("P001"),
            _make_part_row("P002", status=3),
        ]
        result = scraper._scrape_parts()
        assert result.data_type == "part"
        assert len(result.records) == 2
        assert result.records[0]["part_no"] == "P001"
        assert result.records[1]["share_status"] == 3
        assert result.error is None
        mock_client.search_parts.assert_called_once()

    def test_scrape_documents(
        self, scraper: Scraper, mock_client: MagicMock
    ) -> None:
        mock_client.search_documents.return_value = [
            _make_doc_row("D001"),
            _make_doc_row("D002", eai="Failed"),
        ]
        result = scraper._scrape_documents()
        assert result.data_type == "document"
        assert len(result.records) == 2
        assert result.records[0]["document_no"] == "D001"
        assert result.records[1]["eai_message"] == "Failed"

    def test_scrape_conversion(self, scraper: Scraper, mock_client: MagicMock) -> None:
        mock_client.search_conversion.return_value = [
            _make_mq_row("step_ap214"),
            _make_mq_row("step_203"),
            _make_mq_row("step_ap214"),
        ]
        result = scraper._scrape_conversion()
        assert result.data_type == "conversion"
        assert len(result.records) == 2  # only step_ap214
        assert all(r["target_format"] == "step_ap214" for r in result.records)

    def test_empty_parts(self, scraper: Scraper, mock_client: MagicMock) -> None:
        mock_client.search_parts.return_value = []
        result = scraper._scrape_parts()
        assert result.records == []
        assert result.error is None


# ---------------------------------------------------------------------------
# Scraper — error handling
# ---------------------------------------------------------------------------

class TestScraperErrors:
    def test_connection_error_caught(
        self, scraper: Scraper, mock_client: MagicMock
    ) -> None:
        mock_client.search_parts.side_effect = PlmConnectionError("PLM down")
        result = scraper._scrape_single("part", scraper._scrape_parts)
        assert result.data_type == "part"
        assert result.records == []
        assert result.error is not None

    def test_auth_error_caught(
        self, scraper: Scraper, mock_client: MagicMock
    ) -> None:
        mock_client.search_documents.side_effect = PlmAuthError("Bad creds")
        result = scraper._scrape_single(
            "document", scraper._scrape_documents
        )
        assert result.error is not None
        assert "Bad creds" in result.error  # type: ignore[union-attr]

    def test_partial_failure(
        self, scraper: Scraper, mock_client: MagicMock
    ) -> None:
        """One type fails but others still produce results."""
        mock_client.search_parts.side_effect = PlmConnectionError("PLM down")
        mock_client.search_documents.return_value = [_make_doc_row("D001")]
        mock_client.search_conversion.return_value = []

        results = scraper.scrape_all()

        assert results["part"].error is not None
        assert results["part"].records == []
        assert results["document"].error is None
        assert len(results["document"].records) == 1
        assert results["conversion"].error is None


# ---------------------------------------------------------------------------
# Scraper — persistence
# ---------------------------------------------------------------------------

class TestScraperPersistence:
    def test_persist_success(
        self, scraper: Scraper, in_memory_db: Session
    ) -> None:
        result = ScrapeResult(
            data_type="part",
            records=[{"part_no": "P001", "share_status": 9}],
        )
        scraper._persist(result)

        records = in_memory_db.query(ScrapeRecord).all()
        assert len(records) == 1
        assert records[0].data_type == "part"
        assert records[0].raw_data == {"part_no": "P001", "share_status": 9}

        logs = in_memory_db.query(ScrapeLog).all()
        assert len(logs) == 1
        assert logs[0].status == "success"
        assert logs[0].records_count == 1
        assert logs[0].error_message is None
        assert logs[0].completed_at is not None

    def test_persist_error(
        self, scraper: Scraper, in_memory_db: Session
    ) -> None:
        result = ScrapeResult(
            data_type="document",
            error="PLM unreachable",
        )
        scraper._persist(result)

        records = in_memory_db.query(ScrapeRecord).all()
        assert len(records) == 0  # no data saved on error

        logs = in_memory_db.query(ScrapeLog).all()
        assert len(logs) == 1
        assert logs[0].status == "error"
        assert logs[0].error_message == "PLM unreachable"
        assert logs[0].completed_at is None

    def test_persist_multiple_records(
        self, scraper: Scraper, in_memory_db: Session
    ) -> None:
        result = ScrapeResult(
            data_type="conversion",
            records=[
                {"state": "waiting", "target_format": "step_ap214"},
                {"state": "done", "target_format": "step_ap214"},
            ],
        )
        scraper._persist(result)

        records = in_memory_db.query(ScrapeRecord).all()
        assert len(records) == 2
        assert records[0].raw_data["state"] == "waiting"
        assert records[1].raw_data["state"] == "done"


# ---------------------------------------------------------------------------
# End-to-end: scrape_all
# ---------------------------------------------------------------------------

class TestScraperAll:
    def test_scrape_all_success(
        self, scraper: Scraper, mock_client: MagicMock
    ) -> None:
        mock_client.search_parts.return_value = [_make_part_row("P001")]
        mock_client.search_documents.return_value = [_make_doc_row("D001")]
        mock_client.search_conversion.return_value = [
            _make_mq_row("step_ap214"),
        ]

        results = scraper.scrape_all()

        assert set(results) == {"part", "document", "conversion"}
        assert results["part"].error is None
        assert results["document"].error is None
        assert results["conversion"].error is None

        # Verify DB persistence
        records = (
            scraper._db.query(ScrapeRecord)
            .order_by(ScrapeRecord.data_type)
            .all()
        )
        assert len(records) == 3
        assert [r.data_type for r in records] == ["document", "conversion", "part"]

    def test_scrape_all_partial_failure_persists_partial(
        self, scraper: Scraper, mock_client: MagicMock
    ) -> None:
        """Partial failure: only successful types get persisted."""
        mock_client.search_parts.side_effect = PlmConnectionError("Down")
        mock_client.search_documents.return_value = [_make_doc_row("D001")]
        mock_client.search_conversion.return_value = [_make_mq_row("step_ap214")]

        results = scraper.scrape_all()

        assert results["part"].error is not None
        assert results["document"].error is None
        assert results["conversion"].error is None

        # Only successful types should have records
        records = scraper._db.query(ScrapeRecord).all()
        assert len(records) == 2

        logs = scraper._db.query(ScrapeLog).all()
        assert len(logs) == 3  # one log per type regardless of outcome
        error_logs = [log for log in logs if log.status == "error"]
        success_logs = [log for log in logs if log.status == "success"]
        assert len(error_logs) == 1
        assert len(success_logs) == 2
