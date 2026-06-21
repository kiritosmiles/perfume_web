"""002_share_links

Revision ID: 002_share_links
Revises: 1cd116d9a446
Create Date: 2026-06-21 12:00:00.000000

Add share_links table for C4 share feature.
"""

from typing import Sequence, Union
from alembic import op

revision: str = "002_share_links_v1"
down_revision: Union[str, Sequence[str], None] = "1cd116d9a446"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE share_links (
            id CHAR(8) PRIMARY KEY,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days')
        )
    """)
    op.execute("""
        CREATE INDEX idx_share_expires ON share_links (expires_at)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS share_links CASCADE")
