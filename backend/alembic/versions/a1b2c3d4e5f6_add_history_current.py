"""add scrape_history and scrape_current tables

Revision ID: a1b2c3d4e5f6
Revises: dac1f9eb0e15
Create Date: 2026-05-26 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "dac1f9eb0e15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scrape_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data_type", sa.String(), nullable=False),
        sa.Column("raw_data", sa.Text(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scrape_current",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data_type", sa.String(), nullable=False),
        sa.Column("item_key", sa.String(), nullable=False),
        sa.Column("item_index", sa.String(), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_scrape_history_data_type",
        "scrape_history",
        ["data_type"],
    )
    op.create_index(
        "ix_scrape_current_data_type",
        "scrape_current",
        ["data_type"],
    )

    op.create_index(
        "ix_scrape_history_scraped_at",
        "scrape_history",
        ["scraped_at"],
    )
    op.create_index(
        "ix_scrape_current_scraped_at",
        "scrape_current",
        ["scraped_at"],
    )

    op.execute(
        """INSERT INTO scrape_history (data_type, raw_data, scraped_at, created_at, updated_at)
           SELECT data_type, raw_data, scraped_at, created_at, updated_at FROM scrape_records"""
    )


def downgrade() -> None:
    op.drop_table("scrape_current")
    op.drop_table("scrape_history")
