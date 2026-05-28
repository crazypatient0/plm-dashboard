"""DataAccessLayer for typed PLM tables.

Tables:
  part_current / part_history
  document_current / document_history
  conversion_current / conversion_history

History tables use upsert (INSERT OR REPLACE) on natural key.
Current tables use truncate + full insert.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.categorize import categorize_eai_message
from src.exceptions import PlmDataError
from src.logger import get_logger
from src.models import (
    PartCurrent,
    PartHistory,
    DocumentCurrent,
    DocumentHistory,
    ConversionCurrent,
    ConversionHistory,
    ScrapeLog,
)

BJ_TZ = ZoneInfo("Asia/Shanghai")

logger = get_logger(__name__)


class DataAccessLayer:
    def __init__(self, session: Session) -> None:
        self.session = session

    # -------------------------------------------------------------------------
    # Save current (truncate + insert)
    # -------------------------------------------------------------------------

    def save_part_current(self, records: list[dict]) -> int:
        try:
            self.session.execute(delete(PartCurrent))
            now = datetime.now(BJ_TZ)
            if records:
                for r in records:
                    self.session.add(PartCurrent(
                        part_no=r.get("part_no", ""),
                        index_=r.get("index", ""),
                        share_status=r.get("share_status"),
                        sap_info=r.get("sap_info"),
                        scraped_at=now,
                    ))
            else:
                # Insert a placeholder so scraped_at reflects this request time
                self.session.add(PartCurrent(
                    part_no="",
                    index_="",
                    share_status=None,
                    sap_info=None,
                    scraped_at=now,
                ))
            self.session.commit()
            return len(records)
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to save part_current: %s", e)
            raise PlmDataError(f"Failed to save part_current: {e}") from e

    def save_document_current(self, records: list[dict]) -> int:
        try:
            self.session.execute(delete(DocumentCurrent))
            now = datetime.now(BJ_TZ)
            if records:
                for r in records:
                    self.session.add(DocumentCurrent(
                        document_no=r.get("document_no", ""),
                        doc_index=r.get("doc_index", ""),
                        eai_message=r.get("eai_message"),
                        scraped_at=now,
                    ))
            else:
                self.session.add(DocumentCurrent(
                    document_no="",
                    doc_index="",
                    eai_message=None,
                    scraped_at=now,
                ))
            self.session.commit()
            return len(records)
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to save document_current: %s", e)
            raise PlmDataError(f"Failed to save document_current: {e}") from e

    def save_conversion_current(self, records: list[dict]) -> int:
        try:
            self.session.execute(delete(ConversionCurrent))
            now = datetime.now(BJ_TZ)
            if records:
                for r in records:
                    self.session.add(ConversionCurrent(
                        source=r.get("source", ""),
                        state=r.get("state"),
                        target_format=r.get("target_format"),
                        created_utc=r.get("created_utc"),
                        started_utc=r.get("started_utc"),
                        scraped_at=now,
                    ))
            else:
                self.session.add(ConversionCurrent(
                    source="",
                    state=None,
                    target_format=None,
                    created_utc=None,
                    started_utc=None,
                    scraped_at=now,
                ))
            self.session.commit()
            return len(records)
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to save conversion_current: %s", e)
            raise PlmDataError(f"Failed to save conversion_current: {e}") from e

    def save_current(self, data_type: str, records: list[dict]) -> int:
        if data_type == "part":
            return self.save_part_current(records)
        elif data_type == "document":
            return self.save_document_current(records)
        elif data_type == "conversion":
            return self.save_conversion_current(records)
        raise PlmDataError(f"Unknown data_type: {data_type}")

    # -------------------------------------------------------------------------
    # Save history (upsert on natural key)
    # -------------------------------------------------------------------------

    def _upsert_part_history(self, records: list[dict]) -> int:
        if not records:
            return 0
        now = datetime.now(BJ_TZ)
        for r in records:
            part_no = r.get("part_no", "")
            index_ = r.get("index", "")
            sap_info = r.get("sap_info")

            # If new sap_info is NULL, check whether history already has a value
            # Skip upsert entirely to preserve the existing non-NULL status
            if sap_info is None:
                existing = self.session.execute(
                    select(PartHistory.sap_info).where(
                        PartHistory.part_no == part_no,
                        PartHistory.index_ == index_,
                    )
                ).scalar()
                if existing is not None:
                    # Already has non-NULL status; only touch scraped_at to mark it seen
                    self.session.execute(
                        text("""
                            UPDATE part_history
                            SET scraped_at = :now
                            WHERE part_no = :part_no AND index_ = :index_
                        """),
                        {"now": now, "part_no": part_no, "index_": index_},
                    )
                    continue

            self.session.execute(
                sqlite_insert(PartHistory).values(
                    part_no=part_no,
                    index_=index_,
                    share_status=r.get("share_status"),
                    sap_info=sap_info,
                    scraped_at=now,
                    created_at=now,
                ).on_conflict_do_update(
                    index_elements=["part_no", "index_"],
                    set_={
                        "share_status": r.get("share_status"),
                        "sap_info": sap_info,
                        "scraped_at": now,
                    },
                )
            )
        self.session.commit()
        return len(records)

    def _upsert_document_history(self, records: list[dict]) -> int:
        if not records:
            return 0
        now = datetime.now(BJ_TZ)
        for r in records:
            doc_no = r.get("document_no", "")
            doc_idx = r.get("doc_index", "")
            eai_message = r.get("eai_message")

            # If new eai_message is NULL, check whether history already has a value
            # Skip upsert entirely to preserve the existing non-NULL message
            if eai_message is None:
                existing = self.session.execute(
                    select(DocumentHistory.eai_message).where(
                        DocumentHistory.document_no == doc_no,
                        DocumentHistory.doc_index == doc_idx,
                    )
                ).scalar()
                if existing is not None:
                    # Already has non-NULL message; only touch scraped_at to mark it seen
                    self.session.execute(
                        text("""
                            UPDATE document_history
                            SET scraped_at = :now
                            WHERE document_no = :doc_no AND doc_index = :doc_idx
                        """),
                        {"now": now, "doc_no": doc_no, "doc_idx": doc_idx},
                    )
                    continue

            self.session.execute(
                sqlite_insert(DocumentHistory).values(
                    document_no=doc_no,
                    doc_index=doc_idx,
                    eai_message=eai_message,
                    scraped_at=now,
                    created_at=now,
                ).on_conflict_do_update(
                    index_elements=["document_no", "doc_index"],
                    set_={
                        "eai_message": eai_message,
                        "scraped_at": now,
                    },
                )
            )
        self.session.commit()
        return len(records)

    def _upsert_conversion_history(self, records: list[dict]) -> int:
        if not records:
            return 0
        now = datetime.now(BJ_TZ)
        for r in records:
            self.session.execute(
                sqlite_insert(ConversionHistory).values(
                    source=r.get("source", ""),
                    state=r.get("state"),
                    target_format=r.get("target_format"),
                    created_utc=r.get("created_utc"),
                    started_utc=r.get("started_utc"),
                    scraped_at=now,
                    created_at=now,
                ).on_conflict_do_update(
                    index_elements=["source"],
                    set_={
                        "state": r.get("state"),
                        "target_format": r.get("target_format"),
                        "created_utc": r.get("created_utc"),
                        "started_utc": r.get("started_utc"),
                        "scraped_at": now,
                    },
                )
            )
        self.session.commit()
        return len(records)

    def save_history(self, data_type: str, records: list[dict]) -> int:
        if not records:
            return 0
        if data_type == "part":
            return self._upsert_part_history(records)
        elif data_type == "document":
            return self._upsert_document_history(records)
        elif data_type == "conversion":
            return self._upsert_conversion_history(records)
        raise PlmDataError(f"Unknown data_type: {data_type}")

    def save_records(self, data_type: str, records: list[dict]) -> int:
        """Save both history (upsert) and current (replace).

        When records is empty, save_history is skipped but save_current is still
        called so that the current table is truncated and a placeholder row with
        the current timestamp is inserted.
        """
        if records:
            saved_history = self.save_history(data_type, records)
        saved_current = self.save_current(data_type, records)
        return len(records)

    # -------------------------------------------------------------------------
    # Get records
    # -------------------------------------------------------------------------

    def get_current_records(self, data_type: str, limit: int = 100):
        try:
            if data_type == "part":
                stmt = select(PartCurrent).where(PartCurrent.part_no != "").order_by(PartCurrent.scraped_at.desc()).limit(limit)
            elif data_type == "document":
                stmt = select(DocumentCurrent).where(DocumentCurrent.document_no != "").order_by(DocumentCurrent.scraped_at.desc()).limit(limit)
            elif data_type == "conversion":
                stmt = select(ConversionCurrent).where(ConversionCurrent.source != "").order_by(ConversionCurrent.scraped_at.desc()).limit(limit)
            else:
                raise PlmDataError(f"Unknown data_type: {data_type}")
            return list(self.session.execute(stmt).scalars().all())
        except Exception as e:
            logger.error("Failed to get current records: %s", e)
            raise PlmDataError(f"Failed to get current records: {e}") from e

    def get_latest_records(self, data_type: str, limit: int = 100):
        try:
            if data_type == "part":
                stmt = select(PartHistory).order_by(PartHistory.scraped_at.desc()).limit(limit)
            elif data_type == "document":
                stmt = select(DocumentHistory).order_by(DocumentHistory.scraped_at.desc()).limit(limit)
            elif data_type == "conversion":
                stmt = select(ConversionHistory).order_by(ConversionHistory.scraped_at.desc()).limit(limit)
            else:
                raise PlmDataError(f"Unknown data_type: {data_type}")
            return list(self.session.execute(stmt).scalars().all())
        except Exception as e:
            logger.error("Failed to get latest records: %s", e)
            raise PlmDataError(f"Failed to get latest records: {e}") from e

    def get_records_by_time_range(self, data_type: str, since: datetime, until: datetime | None = None):
        try:
            if data_type == "part":
                stmt = select(PartHistory).where(PartHistory.scraped_at >= since)
            elif data_type == "document":
                stmt = select(DocumentHistory).where(DocumentHistory.scraped_at >= since)
            elif data_type == "conversion":
                stmt = select(ConversionHistory).where(ConversionHistory.scraped_at >= since)
            else:
                raise PlmDataError(f"Unknown data_type: {data_type}")
            if until is not None:
                if data_type == "part":
                    stmt = stmt.where(PartHistory.scraped_at < until)
                elif data_type == "document":
                    stmt = stmt.where(DocumentHistory.scraped_at < until)
                else:
                    stmt = stmt.where(ConversionHistory.scraped_at < until)
            order_col = (
                PartHistory.scraped_at if data_type == "part"
                else DocumentHistory.scraped_at if data_type == "document"
                else ConversionHistory.scraped_at
            )
            stmt = stmt.order_by(order_col.desc())
            return list(self.session.execute(stmt).scalars().all())
        except Exception as e:
            logger.error("Failed to get records by time range: %s", e)
            raise PlmDataError(f"Failed to get records by time range: {e}") from e

    def get_records_count(self, data_type: str) -> int:
        try:
            if data_type == "part":
                return self.session.execute(select(func.count(PartHistory.id))).scalar() or 0
            elif data_type == "document":
                return self.session.execute(select(func.count(DocumentHistory.id))).scalar() or 0
            elif data_type == "conversion":
                return self.session.execute(select(func.count(ConversionHistory.id))).scalar() or 0
            raise PlmDataError(f"Unknown data_type: {data_type}")
        except Exception as e:
            logger.error("Failed to get records count: %s", e)
            raise PlmDataError(f"Failed to get records count: {e}") from e

    def get_current_count(self, data_type: str) -> int:
        try:
            if data_type == "part":
                return self.session.execute(
                    select(func.count(PartCurrent.id)).where(PartCurrent.part_no != "")
                ).scalar() or 0
            elif data_type == "document":
                return self.session.execute(
                    select(func.count(DocumentCurrent.id)).where(DocumentCurrent.document_no != "")
                ).scalar() or 0
            elif data_type == "conversion":
                return self.session.execute(
                    select(func.count(ConversionCurrent.id)).where(ConversionCurrent.source != "")
                ).scalar() or 0
            raise PlmDataError(f"Unknown data_type: {data_type}")
        except Exception as e:
            logger.error("Failed to get current count: %s", e)
            raise PlmDataError(f"Failed to get current count: {e}") from e

    def get_summary(self, data_type: str) -> dict:
        try:
            if data_type == "part":
                total = self.get_current_count(data_type)
                latest = self.session.execute(
                    select(func.max(PartCurrent.scraped_at))
                ).scalar()
                oldest = self.session.execute(
                    select(PartHistory.scraped_at).order_by(PartHistory.scraped_at.asc()).limit(1)
                ).scalar()
            elif data_type == "document":
                total = self.get_current_count(data_type)
                latest = self.session.execute(
                    select(func.max(DocumentCurrent.scraped_at))
                ).scalar()
                oldest = self.session.execute(
                    select(DocumentHistory.scraped_at).order_by(DocumentHistory.scraped_at.asc()).limit(1)
                ).scalar()
            elif data_type == "conversion":
                total = self.get_current_count(data_type)
                latest = self.session.execute(
                    select(func.max(ConversionCurrent.scraped_at))
                ).scalar()
                oldest = self.session.execute(
                    select(ConversionHistory.scraped_at).order_by(ConversionHistory.scraped_at.asc()).limit(1)
                ).scalar()
            else:
                raise PlmDataError(f"Unknown data_type: {data_type}")

            return {
                "total": total,
                "latest_scraped_at": latest,
                "oldest_scraped_at": oldest,
            }
        except Exception as e:
            logger.error("Failed to get summary: %s", e)
            raise PlmDataError(f"Failed to get summary: {e}") from e

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def search_records(self, data_type: str, field: str, value: str):
        try:
            if data_type == "part":
                all_records: list = list(self.session.execute(select(PartHistory)).scalars().all())
            elif data_type == "document":
                all_records = list(self.session.execute(select(DocumentHistory)).scalars().all())
            elif data_type == "conversion":
                all_records = list(self.session.execute(select(ConversionHistory)).scalars().all())
            else:
                raise PlmDataError(f"Unknown data_type: {data_type}")

            matched = []
            for record in all_records:
                raw = {c.name: getattr(record, c.name) for c in record.__table__.columns}
                field_val = raw.get(field)
                if field_val is not None and value.lower() in str(field_val).lower():
                    matched.append(record)
            return matched
        except Exception as e:
            logger.error("Failed to search records: %s", e)
            raise PlmDataError(f"Failed to search records: {e}") from e

    # -------------------------------------------------------------------------
    # Prune / delete
    # -------------------------------------------------------------------------

    def prune_old_data(self, retention_days: int) -> int:
        try:
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            total = 0
            for model in [PartHistory, DocumentHistory, ConversionHistory]:
                stmt = delete(model).where(model.scraped_at < cutoff)
                result = self.session.execute(stmt)
                total += result.rowcount
            self.session.commit()
            return total
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to prune old data: %s", e)
            raise PlmDataError(f"Failed to prune old data: {e}") from e

    def delete_all_history(self, data_type: str | None = None) -> int:
        try:
            total = 0
            if data_type is None or data_type == "part":
                r = self.session.execute(delete(PartHistory))
                total += r.rowcount
            if data_type is None or data_type == "document":
                r = self.session.execute(delete(DocumentHistory))
                total += r.rowcount
            if data_type is None or data_type == "conversion":
                r = self.session.execute(delete(ConversionHistory))
                total += r.rowcount
            self.session.commit()
            return total
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

    def get_recent_logs(self, data_type: str | None = None, limit: int = 20):
        try:
            stmt = select(ScrapeLog)
            if data_type is not None:
                stmt = stmt.where(ScrapeLog.data_type == data_type)
            stmt = stmt.order_by(ScrapeLog.started_at.desc()).limit(limit)
            return list(self.session.execute(stmt).scalars().all())
        except Exception as e:
            logger.error("Failed to get recent logs: %s", e)
            raise PlmDataError(f"Failed to get recent logs: {e}") from e

    def save_log(self, entry: ScrapeLog) -> None:
        try:
            self.session.add(entry)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to save log: %s", e)
            raise PlmDataError(f"Failed to save log: {e}") from e

    # -------------------------------------------------------------------------
    # Part stats (for visualization)
    # -------------------------------------------------------------------------

    def get_part_stats(self) -> dict:
        """Compute part history stats for visualization.

        Uses FULL history table (all records), grouped by sap_info category.
        Returns category breakdown, daily stacked breakdown, and current_count as baseline.
        """
        def categorize(sap_info: str | None) -> str:
            s = (sap_info or "").strip()
            if not s:
                return "Normal"
            if "SAP template not filled" in s:
                return "TemplateNotFilled"
            if "MigParts prevent" in s:
                return "MigPartsBlocked"
            return "Normal"

        try:
            # Get full history rows
            history_rows = self.session.execute(
                select(PartHistory.part_no, PartHistory.sap_info, PartHistory.scraped_at)
                .order_by(PartHistory.scraped_at)
            ).fetchall()

            # Category breakdown
            from collections import Counter
            cat_counter = Counter(categorize(r[1]) for r in history_rows)

            # Daily breakdown
            daily: dict[str, dict[str, int]] = {}
            for r in history_rows:
                scraped_at: datetime = r[2]
                day = scraped_at.strftime("%Y-%m-%d") if scraped_at else "unknown"
                if day not in daily:
                    daily[day] = {"Normal": 0, "MigPartsBlocked": 0, "TemplateNotFilled": 0}
                cat = categorize(r[1])
                daily[day][cat] += 1

            daily_breakdown = sorted(
                [{"date": d, **counts} for d, counts in daily.items()],
                key=lambda x: x["date"],
            )

            # Current count as baseline for percentages
            current_count = self.get_current_count("part")

            return {
                "category_breakdown": [
                    {"name": "Normal", "value": cat_counter.get("Normal", 0)},
                    {"name": "MigPartsBlocked", "value": cat_counter.get("MigPartsBlocked", 0)},
                    {"name": "TemplateNotFilled", "value": cat_counter.get("TemplateNotFilled", 0)},
                ],
                "daily_breakdown": daily_breakdown,
                "current_count": current_count,
            }
        except Exception as e:
            logger.error("Failed to get part stats: %s", e)
            raise PlmDataError(f"Failed to get part stats: {e}") from e

    # -------------------------------------------------------------------------
    # Document stats (for visualization)
    # -------------------------------------------------------------------------

    def get_document_stats(self) -> dict:
        """Compute document history stats for visualization.

        Uses FULL history table (all records), categorized by EAI message.
        Returns category breakdown and daily stacked breakdown.
        """
        ALL_CATEGORIES = ["Normal", "StatusFlowError", "MissingOriginals"]

        try:
            # Get full history rows with COALESCE to handle NULL eai_message
            history_rows = self.session.execute(
                select(
                    DocumentHistory.document_no,
                    func.coalesce(DocumentHistory.eai_message, ''),
                    DocumentHistory.scraped_at,
                )
                .order_by(DocumentHistory.scraped_at)
            ).fetchall()

            # Category breakdown
            from collections import defaultdict
            category_breakdown: dict[str, int] = defaultdict(int)
            daily: dict[str, dict[str, int]] = {}

            for row in history_rows:
                _doc_no, eai_message, scraped_at = row
                cat = categorize_eai_message(eai_message)
                category_breakdown[cat] += 1

                day = scraped_at.strftime("%Y-%m-%d") if scraped_at else "unknown"
                if day not in daily:
                    daily[day] = {c: 0 for c in ALL_CATEGORIES}
                daily[day][cat] += 1

            # Ensure all categories are present in category_breakdown
            for cat in ALL_CATEGORIES:
                if cat not in category_breakdown:
                    category_breakdown[cat] = 0

            daily_breakdown = sorted(
                [{"date": d, "categories": counts} for d, counts in daily.items()],
                key=lambda x: x["date"],
            )

            return {
                "total": sum(category_breakdown.values()),
                "category_breakdown": dict(category_breakdown),
                "daily_breakdown": daily_breakdown,
            }
        except Exception as e:
            logger.error("Failed to get document stats: %s", e)
            raise PlmDataError(f"Failed to get document stats: {e}") from e

    def get_conversion_stats(self) -> dict:
        """Compute conversion current stats for the race-track visualization.

        Each conversion job's wait time is computed as:
            wait_seconds = scraped_at (Asia/Shanghai) - created_utc (UTC)
        Jobs are sorted: failed FIRST, then by wait_seconds descending (longest wait = front).
        """
        try:
            rows = self.session.execute(
                select(
                    ConversionCurrent.source,
                    ConversionCurrent.state,
                    ConversionCurrent.target_format,
                    ConversionCurrent.created_utc,
                    ConversionCurrent.scraped_at,
                )
            ).fetchall()

            items: list[dict] = []
            for r in rows:
                source, state, target_format, created_utc_str, scraped_at = r
                wait_seconds: float | None = None
                if created_utc_str and scraped_at:
                    try:
                        created_utc_dt = datetime.fromisoformat(
                            created_utc_str.replace("Z", "+00:00")
                        )
                        # Treat created_utc as UTC, scraped_at as BJ
                        created_aware = created_utc_dt.replace(tzinfo=BJ_TZ)
                        scraped_aware = scraped_at if scraped_at.tzinfo else scraped_at.replace(tzinfo=BJ_TZ)
                        delta = scraped_aware - created_aware
                        wait_seconds = delta.total_seconds()
                        if wait_seconds < 0:
                            wait_seconds = 0  # guard against clock skew
                    except Exception:
                        wait_seconds = None

                items.append({
                    "source": source or "",
                    "state": state or "unknown",
                    "target_format": target_format or "",
                    "created_utc": created_utc_str,
                    "wait_seconds": wait_seconds,
                })

            # Sort: failed first, then longest wait descending
            items.sort(
                key=lambda x: (
                    0 if x["state"].lower() == "failed" else 1,
                    -x["wait_seconds"] if x["wait_seconds"] is not None else -float("inf"),
                )
            )

            failed_count = sum(1 for x in items if x["state"].lower() == "failed")

            return {
                "total": len(items),
                "failed_count": failed_count,
                "items": items,
            }
        except Exception as e:
            logger.error("Failed to get conversion stats: %s", e)
            raise PlmDataError(f"Failed to get conversion stats: {e}") from e
