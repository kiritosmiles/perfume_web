"""006_user_profiles

Revision ID: 006_user_profiles
Revises: 005_feedback
Create Date: 2026-06-23 23:00:00.000000

Add user_profiles table for Phase 3 user profiling (FR-1.1, FR-1.3).
Stores structured profile data as JSONB with conversation count for
progressive profile building (light mode first 3 sessions, full mode
from session 4 onward).
"""

from typing import Sequence, Union
from alembic import op

revision: str = "006_user_profiles"
down_revision: Union[str, Sequence[str], None] = "005_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_profiles (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            profile_data JSONB NOT NULL DEFAULT '{
                "personality_tags": [],
                "emotion_tendency": {},
                "preferred_accords": [],
                "preferred_notes": [],
                "gift_history": [],
                "profile_level": "light",
                "questionnaire_completed": false
            }'::jsonb,
            conversation_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX idx_user_profiles_updated
        ON user_profiles (updated_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_profiles CASCADE")
