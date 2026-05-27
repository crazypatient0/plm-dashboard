from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.exceptions import PlmDataError
from src.logger import get_logger
from src.models import ScrapeCurrent, ScrapeHistory, ScrapeLog, ScrapeRecord

# Beijing timezone for scraped_at timestamps
BJ_TZ = ZoneInfo("Asia/Shanghai")

logger = get_logger(__name__)


class DataAccessLayer:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_item_key_index(self, data_type: str, record: dict) -> tuple[str, str | None]:
        if data_type == "part":
            return record.get("part_no", ""), record.get("index")
        elif data_type == "document":
            return record.get("document_no", ""), record.get("doc_index")
        elif data_type == "conversion":
            return record.get("started_utc", "") or "", None
        return "", None

    def save_history(self, data_type: str, records: list[dict]) -> int:
        if not records:
            return 0
        try:
            cutoff = datetime.now(UTC) - timedelta(minutes=5)
            existing = (
                self.session.execute(
                    select(ScrapeHistory).where(
                        ScrapeHistory.data_type == data_type,
                        ScrapeHistory.scraped_at >= cutoff,
                    )
                )
                .scalars()
                .all()
            )

            existing_serials = {
                json.dumps(r.raw_data, sort_keys=True, default=str) for r in existing
            }

            to_insert: list[ScrapeHistory] = []
            skipped = 0
            for record in records:
                serial = json.dumps(record, sort_keys=True, default=str)
                if serial in existing_serials:
                    skipped += 1
                    continue
                to_insert.append(
                    ScrapeHistory(
                        data_type=data_type,
                        raw_data=record,
                        scraped_at=datetime.now(BJ_TZ),
                    )
                )

            if skipped:
                logger.warning("Skipped %d duplicate history records for %s", skipped, data_type)

            if to_insert:
                self.session.add_all(to_insert)
                self.session.commit()
            return len(to_insert)
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to save history for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to save history: {e}") from e

    def save_current(self, data_type: str, records: list[dict]) -> int:
        if not records:
            return 0
        try:
            # DELETE ALL existing records for this data_type before inserting new batch
            # This ensures scrape_current always reflects ONLY the latest scrape
            self.session.execute(delete(ScrapeCurrent).where(ScrapeCurrent.data_type == data_type))

            scrape_time = datetime.now(BJ_TZ)
            for record in records:
                item_key, item_index = self._get_item_key_index(data_type, record)
                self.session.add(
                    ScrapeCurrent(
                        data_type=data_type,
                        item_key=item_key,
                        item_index=item_index,
                        raw_data=record,
                        scraped_at=scrape_time,
                    )
                )

            self.session.commit()
            return len(records)
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to save current for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to save current: {e}") from e

    def save_records(self, data_type: str, records: list[dict]) -> int:
        if not records:
            return 0
        saved_history = self.save_history(data_type, records)
        saved_current = self.save_current(data_type, records)
        return saved_history

    def save_log(self, entry: ScrapeLog) -> None:
        try:
            self.session.add(entry)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to save log: %s", e)
            raise PlmDataError(f"Failed to save log: {e}") from e

    def get_current_records(self, data_type: str, limit: int = 100) -> list[ScrapeCurrent]:
        try:
            stmt = (
                select(ScrapeCurrent)
                .where(ScrapeCurrent.data_type == data_type)
                .order_by(ScrapeCurrent.scraped_at.desc())
                .limit(limit)
            )
            return list(self.session.execute(stmt).scalars().all())
        except Exception as e:
            logger.error("Failed to get current records for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to get current records: {e}") from e

    def get_latest_records(self, data_type: str, limit: int = 100) -> list[ScrapeHistory]:
        try:
            stmt = (
                select(ScrapeHistory)
                .where(ScrapeHistory.data_type == data_type)
                .order_by(ScrapeHistory.scraped_at.desc())
                .limit(limit)
            )
            return list(self.session.execute(stmt).scalars().all())
        except Exception as e:
            logger.error("Failed to get latest records for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to get latest records: {e}") from e

    def get_records_by_time_range(
        self,
        data_type: str,
        since: datetime,
        until: datetime | None = None,
    ) -> list[ScrapeHistory]:
        try:
            stmt = select(ScrapeHistory).where(
                ScrapeHistory.data_type == data_type,
                ScrapeHistory.scraped_at >= since,
            )
            if until is not None:
                stmt = stmt.where(ScrapeHistory.scraped_at < until)
            stmt = stmt.order_by(ScrapeHistory.scraped_at.desc())
            return list(self.session.execute(stmt).scalars().all())
        except Exception as e:
            logger.error("Failed to get records by time range for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to get records by time range: {e}") from e

    def get_records_count(self, data_type: str) -> int:
        try:
            stmt = select(func.count(ScrapeHistory.id)).where(ScrapeHistory.data_type == data_type)
            result = self.session.execute(stmt).scalar()
            return result or 0
        except Exception as e:
            logger.error("Failed to get records count for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to get records count: {e}") from e

    def get_current_count(self, data_type: str) -> int:
        try:
            stmt = select(func.count(ScrapeCurrent.id)).where(ScrapeCurrent.data_type == data_type)
            result = self.session.execute(stmt).scalar()
            return result or 0
        except Exception as e:
            logger.error("Failed to get current count for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to get current count: {e}") from e

    def get_summary(self, data_type: str) -> dict:
        try:
            # total = current snapshot count (latest scrape results)
            total = self.get_current_count(data_type)
            # latest_scraped_at = most recent scrape time (from current snapshot, Beijing time)
            stmt_latest = (
                select(func.max(ScrapeCurrent.scraped_at))
                .where(ScrapeCurrent.data_type == data_type)
            )
            # oldest_scraped_at = earliest scrape time in history
            stmt_oldest = (
                select(ScrapeHistory.scraped_at)
                .where(ScrapeHistory.data_type == data_type)
                .order_by(ScrapeHistory.scraped_at.asc())
                .limit(1)
            )

            latest = self.session.execute(stmt_latest).scalar()
            oldest = self.session.execute(stmt_oldest).scalar()

            return {
                "total": total,
                "latest_scraped_at": latest,
                "oldest_scraped_at": oldest,
            }
        except Exception as e:
            logger.error("Failed to get summary for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to get summary: {e}") from e

    def get_recent_logs(
        self,
        data_type: str | None = None,
        limit: int = 20,
    ) -> list[ScrapeLog]:
        try:
            stmt = select(ScrapeLog)
            if data_type is not None:
                stmt = stmt.where(ScrapeLog.data_type == data_type)
            stmt = stmt.order_by(ScrapeLog.started_at.desc()).limit(limit)
            return list(self.session.execute(stmt).scalars().all())
        except Exception as e:
            logger.error("Failed to get recent logs: %s", e)
            raise PlmDataError(f"Failed to get recent logs: {e}") from e

    def prune_old_data(self, retention_days: int) -> int:
        try:
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            stmt = delete(ScrapeHistory).where(ScrapeHistory.scraped_at < cutoff)
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to prune old data: %s", e)
            raise PlmDataError(f"Failed to prune old data: {e}") from e

    def delete_all_history(self, data_type: str | None = None) -> int:
        """Delete ALL records from scrape_history table. Used to start fresh."""
        try:
            stmt = delete(ScrapeHistory)
            if data_type is not None:
                stmt = stmt.where(ScrapeHistory.data_type == data_type)
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to delete all history: %s", e)
            raise PlmDataError(f"Failed to delete all history: {e}") from e

    def prune_old_logs(self, retention_days: int) -> int:
        try:
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            stmt = delete(ScrapeLog).where(ScrapeLog.started_at < cutoff)
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to prune old logs: %s", e)
            raise PlmDataError(f"Failed to prune old logs: {e}") from e

    def search_records(
        self,
        data_type: str,
        field: str,
        value: str,
    ) -> list[ScrapeHistory]:
        try:
            stmt = select(ScrapeHistory).where(ScrapeHistory.data_type == data_type)
            all_records = list(self.session.execute(stmt).scalars().all())
            matched = []
            for record in all_records:
                raw = record.raw_data
                if isinstance(raw, dict):
                    field_val = raw.get(field)
                    if field_val is not None and value.lower() in str(field_val).lower():
                        matched.append(record)
            return matched
        except Exception as e:
            logger.error("Failed to search records for %s: %s", data_type, e)
            raise PlmDataError(f"Failed to search records: {e}") from e
