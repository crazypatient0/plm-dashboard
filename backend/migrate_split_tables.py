"""Migration script: split unified scrape_history/scrape_current tables
into typed tables for part, document, conversion.

Upsert logic:
  - current tables : truncate + full insert (no unique key on data)
  - history tables : INSERT OR REPLACE on natural key
      part_history      (part_no, index)
      document_history  (document_no, doc_index)
      conversion_history (source)
"""

import json
import sqlite3
import sys
from datetime import datetime

SRC_DB = "plm_dashboard.db"
BACKUP_DB = "plm_dashboard.db.backup_migration"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def migrate() -> None:
    log("Starting migration...")

    # 1. Backup
    import shutil
    shutil.copy2(SRC_DB, BACKUP_DB)
    log(f"Backup created: {BACKUP_DB}")

    conn = sqlite3.connect(SRC_DB)
    cur = conn.cursor()

    # 2. Create new typed tables
    log("Creating new typed tables...")

    # -- Part tables (no JSON, typed columns) --
    cur.execute("""
        CREATE TABLE IF NOT EXISTS part_current (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            part_no      VARCHAR(50)  NOT NULL,
            index_       VARCHAR(10)  NOT NULL,
            share_status INTEGER,
            sap_info     TEXT,
            scraped_at   DATETIME NOT NULL,
            created_at   DATETIME NOT NULL,
            updated_at   DATETIME
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS part_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            part_no      VARCHAR(50)  NOT NULL,
            index_       VARCHAR(10)  NOT NULL,
            share_status INTEGER,
            sap_info     TEXT,
            scraped_at   DATETIME NOT NULL,
            created_at   DATETIME NOT NULL,
            UNIQUE(part_no, index_)
        )
    """)

    # -- Document tables --
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_current (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            document_no   VARCHAR(50)  NOT NULL,
            doc_index     VARCHAR(10)  NOT NULL,
            eai_message   TEXT,
            scraped_at    DATETIME NOT NULL,
            created_at    DATETIME NOT NULL,
            updated_at    DATETIME
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            document_no   VARCHAR(50)  NOT NULL,
            doc_index     VARCHAR(10)  NOT NULL,
            eai_message   TEXT,
            scraped_at    DATETIME NOT NULL,
            created_at    DATETIME NOT NULL,
            UNIQUE(document_no, doc_index)
        )
    """)

    # -- Conversion tables --
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversion_current (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            source         VARCHAR(255) NOT NULL,
            state          VARCHAR(50),
            target_format  VARCHAR(50),
            created_utc   TEXT,
            started_utc   TEXT,
            scraped_at    DATETIME NOT NULL,
            created_at    DATETIME NOT NULL,
            updated_at    DATETIME
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversion_history (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            source         VARCHAR(255) NOT NULL UNIQUE,
            state          VARCHAR(50),
            target_format  VARCHAR(50),
            created_utc   TEXT,
            started_utc   TEXT,
            scraped_at    DATETIME NOT NULL,
            created_at    DATETIME NOT NULL,
            UNIQUE(source)
        )
    """)

    conn.commit()
    log("New tables created.")

    # 3. Migrate scrape_history -> typed history tables
    log("Migrating scrape_history...")

    cur.execute("SELECT id, raw_data, scraped_at, created_at FROM scrape_history WHERE data_type = 'part'")
    for row in cur.fetchall():
        _, raw_json, scraped_at, created_at = row
        d = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        cur.execute("""
            INSERT OR REPLACE INTO part_history (part_no, index_, share_status, sap_info, scraped_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            d.get("part_no", ""),
            d.get("index", ""),
            d.get("share_status"),
            d.get("sap_info"),
            scraped_at,
            created_at,
        ))
    log("  part_history: done")

    cur.execute("SELECT id, raw_data, scraped_at, created_at FROM scrape_history WHERE data_type = 'document'")
    for row in cur.fetchall():
        _, raw_json, scraped_at, created_at = row
        d = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        cur.execute("""
            INSERT OR REPLACE INTO document_history (document_no, doc_index, eai_message, scraped_at, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            d.get("document_no", ""),
            d.get("doc_index", ""),
            d.get("eai_message"),
            scraped_at,
            created_at,
        ))
    log("  document_history: done")

    cur.execute("SELECT id, raw_data, scraped_at, created_at FROM scrape_history WHERE data_type = 'conversion'")
    for row in cur.fetchall():
        _, raw_json, scraped_at, created_at = row
        d = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        cur.execute("""
            INSERT OR REPLACE INTO conversion_history (source, state, target_format, created_utc, started_utc, scraped_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("source", ""),
            d.get("state"),
            d.get("target_format"),
            d.get("created_utc"),
            d.get("started_utc"),
            scraped_at,
            created_at,
        ))
    log("  conversion_history: done")

    conn.commit()

    # 4. Migrate scrape_current -> typed current tables
    log("Migrating scrape_current...")

    cur.execute("DELETE FROM part_current")
    cur.execute("DELETE FROM document_current")
    cur.execute("DELETE FROM conversion_current")

    cur.execute("SELECT id, raw_data, scraped_at, created_at FROM scrape_current WHERE data_type = 'part'")
    for row in cur.fetchall():
        _, raw_json, scraped_at, created_at = row
        d = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        cur.execute("""
            INSERT INTO part_current (part_no, index_, share_status, sap_info, scraped_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            d.get("part_no", ""),
            d.get("index", ""),
            d.get("share_status"),
            d.get("sap_info"),
            scraped_at,
            created_at,
        ))
    log("  part_current: done")

    cur.execute("SELECT id, raw_data, scraped_at, created_at FROM scrape_current WHERE data_type = 'document'")
    for row in cur.fetchall():
        _, raw_json, scraped_at, created_at = row
        d = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        cur.execute("""
            INSERT INTO document_current (document_no, doc_index, eai_message, scraped_at, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            d.get("document_no", ""),
            d.get("doc_index", ""),
            d.get("eai_message"),
            scraped_at,
            created_at,
        ))
    log("  document_current: done")

    cur.execute("SELECT id, raw_data, scraped_at, created_at FROM scrape_current WHERE data_type = 'conversion'")
    for row in cur.fetchall():
        _, raw_json, scraped_at, created_at = row
        d = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        cur.execute("""
            INSERT INTO conversion_current (source, state, target_format, created_utc, started_utc, scraped_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("source", ""),
            d.get("state"),
            d.get("target_format"),
            d.get("created_utc"),
            d.get("started_utc"),
            scraped_at,
            created_at,
        ))
    log("  conversion_current: done")

    conn.commit()

    # 5. Drop old tables
    log("Dropping old tables...")
    cur.execute("DROP TABLE IF EXISTS scrape_history")
    cur.execute("DROP TABLE IF EXISTS scrape_current")
    conn.commit()
    log("Old tables dropped.")

    # 6. Report counts
    log("Verification:")
    for table in ["part_current", "part_history",
                  "document_current", "document_history",
                  "conversion_current", "conversion_history"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cur.fetchone()[0]} rows")

    conn.close()
    log("Migration complete!")


if __name__ == "__main__":
    migrate()
