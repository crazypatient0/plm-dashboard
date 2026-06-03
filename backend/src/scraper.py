"""PLM data scraper service.

Orchestrates data collection from three PIA PLM query types and persists
the results to the local database.

Column index mappings verified from live PLM API responses (2026-05-25):

**Parts** (78 columns):
  col[6]  = part_no
  col[7]  = index
  col[13] = share_status
  col[62] = sap_info

**Documents** (39 columns):
  col[3]  = document_no
  col[4]  = doc_index
  col[35] = eai_message

**MQ ACS** (13 columns):
  col[1]  = state
  col[4]  = target_format
  col[5]  = created_utc
  col[6]  = started_utc
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session as DBSession

from src.exceptions import PlmBaseError
from src.models import ScrapeLog
from src.plm_client import PlmClient
from src.storage import DataAccessLayer

BJ_TZ = ZoneInfo("Asia/Shanghai")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column index mappings
# ---------------------------------------------------------------------------

PARTS_COLUMNS: dict[str, int] = {
    "part_no": 6,
    "index": 7,
    "share_status": 13,
    "sap_info": 62,
}

DOCUMENTS_COLUMNS: dict[str, int] = {
    "document_no": 3,
    "doc_index": 4,
    "eai_message": 35,
}

MQ_ACS_COLUMNS: dict[str, int] = {
    "state": 1,
    "source": 2,
    "target_format": 4,
    "created_utc": 5,
    "started_utc": 6,
}


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

def _extract_columns(
    row: dict[str, Any], column_map: dict[str, int]
) -> dict[str, Any]:
    """Extract mapped fields from a PLM search result row.

    Each PLM row is a dict with a ``"columns"`` key holding a list of
    cell values in the order defined by the search definition.
    """
    cols: list[Any] = row.get("columns") or []
    result: dict[str, Any] = {}
    for field_name, idx in column_map.items():
        result[field_name] = cols[idx] if idx < len(cols) else None
    return result


def _filter_conversion(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter conversion records: keep only target_format=step_ap214 (any state)."""
    return [
        r for r in records
        if r.get("target_format") == "step_ap214"
    ]


# ---------------------------------------------------------------------------
# Per-type scrape result
# ---------------------------------------------------------------------------

@dataclass
class ScrapeResult:
    """Result of scraping a single PLM query type."""

    data_type: str
    records: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class Scraper:
    """Orchestrates PLM data scraping across three query types.

    Usage::

        scraper = Scraper(plm_client, db_session)
        result = scraper.scrape_all()  # returns dict with per-type status
    """

    def __init__(self, client: PlmClient, db: DBSession) -> None:
        self._client = client
        self._db = db

    # ---- Public API -------------------------------------------------------

    def scrape_all(self) -> dict[str, ScrapeResult]:
        """Run all three scrape queries and persist results to DB.

    Each query type is executed independently so that one failure does not
        prevent the other types from being collected.

        Returns a dict mapping ``data_type`` → ``ScrapeResult``.
        """
        type_map: dict[str, ScrapeResult] = {}

        parts = self._scrape_single("part", self._scrape_parts)
        documents = self._scrape_single("document", self._scrape_documents)
        conversion = self._scrape_single("conversion", self._scrape_conversion)

        for result in (parts, documents, conversion):
            self._persist(result)
            type_map[result.data_type] = result

        return type_map

    # ---- Individual query helpers ----------------------------------------

    def _scrape_parts(self) -> ScrapeResult:
        """Fetch and extract parts data."""
        raw_rows = self._client.search_parts()
        extracted = [_extract_columns(r, PARTS_COLUMNS) for r in raw_rows]
        return ScrapeResult(data_type="part", records=extracted)

    def _scrape_documents(self) -> ScrapeResult:
        """Fetch and extract document data."""
        raw_rows = self._client.search_documents()
        extracted = [_extract_columns(r, DOCUMENTS_COLUMNS) for r in raw_rows]
        return ScrapeResult(data_type="document", records=extracted)

    def _scrape_conversion(self) -> ScrapeResult:
        """Fetch, extract and filter MQ ACS data."""
        raw_rows = self._client.search_conversion()
        extracted = [_extract_columns(r, MQ_ACS_COLUMNS) for r in raw_rows]
        records = _filter_conversion(extracted)
        return ScrapeResult(data_type="conversion", records=records)

    # ---- Persistence -----------------------------------------------------

    def _scrape_single(
        self,
        data_type: str,
        scrape_fn: Any,
    ) -> ScrapeResult:
        """Execute *scrape_fn* and return a ``ScrapeResult``.

        Any ``PlmBaseError`` (or subclass) is caught and recorded in the
        result rather than propagated.
        """
        try:
            return scrape_fn()
        except PlmBaseError as exc:
            logger.warning("Scrape '%s' failed: %s", data_type, exc)
            return ScrapeResult(data_type=data_type, error=str(exc))

    def _persist(self, result: ScrapeResult) -> None:
        """Write one scrape result to the database.

        Both the raw records (history + current) and a ``ScrapeLog`` entry
        are created inside a single transaction via the DataAccessLayer.
        """
        started_at = datetime.now(BJ_TZ)
        try:
            dal = DataAccessLayer(session=self._db)
            if result.error is None:
                saved_count = dal.save_records(result.data_type, result.records)

                status = "success"
                records_count = saved_count
                error_message: str | None = None
            else:
                status = "error"
                records_count = 0
                error_message = result.error

            self._db.add(
                ScrapeLog(
                    data_type=result.data_type,
                    status=status,
                    records_count=records_count,
                    error_message=error_message,
                    started_at=started_at,
                    completed_at=datetime.now(BJ_TZ) if result.error is None else None,
                )
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
