"""004_memory

Revision ID: 004_memory
Revises: 003_users
Create Date: 2026-06-21 18:00:00.000000

Add memory_l2 and memory_l3 tables with pgvector indexes.
"""

from typing import Sequence, Union
from alembic import op

revision: str = "004_memory"
down_revision: Union[str, Sequence[str], None] = "003_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE memory_l2 (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            browser_id TEXT,
            session_id UUID NOT NULL,
            text TEXT NOT NULL,
            embedding vector(512),
            emotion_profile JSONB DEFAULT '{}',
            round_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_memory_l2_owner CHECK (
                (user_id IS NOT NULL AND browser_id IS NULL)
                OR (user_id IS NULL AND browser_id IS NOT NULL)
            )
        )
    """)
    op.execute("CREATE INDEX idx_memory_l2_user ON memory_l2 (user_id, created_at)")
    op.execute("CREATE INDEX idx_memory_l2_browser ON memory_l2 (browser_id, created_at)")
    op.execute("CREATE INDEX idx_memory_l2_embedding ON memory_l2 USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")

    op.execute("""
        CREATE TABLE memory_l3 (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            browser_id TEXT,
            date DATE NOT NULL,
            text TEXT NOT NULL,
            embedding vector(512),
            preference_keywords TEXT[],
            session_count INTEGER NOT NULL DEFAULT 0,
            emotion_summary JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (user_id, date),
            UNIQUE (browser_id, date),
            CONSTRAINT chk_memory_l3_owner CHECK (
                (user_id IS NOT NULL AND browser_id IS NULL)
                OR (user_id IS NULL AND browser_id IS NOT NULL)
            )
        )
    """)
    op.execute("CREATE INDEX idx_memory_l3_user ON memory_l3 (user_id, date)")
    op.execute("CREATE INDEX idx_memory_l3_browser ON memory_l3 (browser_id, date)")
    op.execute("CREATE INDEX idx_memory_l3_embedding ON memory_l3 USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_l3 CASCADE")
    op.execute("DROP TABLE IF EXISTS memory_l2 CASCADE")
