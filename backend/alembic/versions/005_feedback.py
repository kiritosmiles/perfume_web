"""005_feedback

Revision ID: 005_feedback
Revises: 004_memory
Create Date: 2026-06-23 20:00:00.000000

Add feedback table for explicit (like/dislike) and implicit (dwell, share, refine) events.
"""

from typing import Sequence, Union
from alembic import op

revision: str = "005_feedback"
down_revision: Union[str, Sequence[str], None] = "004_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            browser_id TEXT,
            generation_id UUID NOT NULL,
            feedback_type VARCHAR(16) NOT NULL CHECK (feedback_type IN ('explicit', 'implicit')),
            event_name VARCHAR(64) NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_feedback_owner CHECK (
                (user_id IS NOT NULL AND browser_id IS NULL)
                OR (user_id IS NULL AND browser_id IS NOT NULL)
                OR (user_id IS NULL AND browser_id IS NULL)
            )
        )
    """)
    op.execute("CREATE INDEX idx_feedback_user_time ON feedback (user_id, created_at)")
    op.execute("CREATE INDEX idx_feedback_browser_time ON feedback (browser_id, created_at)")
    op.execute("CREATE INDEX idx_feedback_gen_id ON feedback (generation_id)")
    op.execute("CREATE INDEX idx_feedback_type ON feedback (feedback_type)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feedback")
