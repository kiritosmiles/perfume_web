"""003_users

Revision ID: 003_users
Revises: 002_share_links_v1
Create Date: 2026-06-21 13:00:00.000000

Add users, refresh_tokens, user_quota tables.
Modify temp_conversations to add user_id FK.
"""

from typing import Sequence, Union
from alembic import op

revision: str = "003_users"
down_revision: Union[str, Sequence[str], None] = "002_share_links_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table 1: users ────────────────────────────────────────
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ── Table 2: refresh_tokens ───────────────────────────────
    op.execute("""
        CREATE TABLE refresh_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id)
    """)

    # ── Table 3: user_quota ───────────────────────────────────
    op.execute("""
        CREATE TABLE user_quota (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            quota_type VARCHAR(32) NOT NULL CHECK (quota_type IN ('sessions', 'generations', 'deep')),
            used INTEGER NOT NULL DEFAULT 0,
            reset_at DATE NOT NULL DEFAULT CURRENT_DATE,
            PRIMARY KEY (user_id, quota_type, reset_at)
        )
    """)

    # ── Table 4: temp_conversations — add user_id ─────────────
    op.execute("""
        ALTER TABLE temp_conversations ADD COLUMN user_id UUID REFERENCES users(id)
    """)
    op.execute("""
        CREATE INDEX idx_temp_conv_user ON temp_conversations (user_id, created_at)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE temp_conversations DROP COLUMN IF EXISTS user_id CASCADE")
    op.execute("DROP TABLE IF EXISTS user_quota CASCADE")
    op.execute("DROP TABLE IF EXISTS refresh_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
