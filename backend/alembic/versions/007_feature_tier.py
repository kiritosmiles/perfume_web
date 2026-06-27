"""007_feature_tier

Revision ID: 007_feature_tier
Revises: 006_user_profiles
Create Date: 2026-06-25 14:00:00.000000

Add feature_tier column to users table for Phase 4 free/premium tier
differentiation. Defaults to 'free' for all existing users.
"""

from typing import Sequence, Union
from alembic import op

revision: str = "007_feature_tier"
down_revision: Union[str, Sequence[str], None] = "006_user_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Split into individual statements — asyncpg rejects multi-command prepared statements
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS feature_tier VARCHAR(16) NOT NULL DEFAULT 'free'")
    op.execute("ALTER TABLE users ADD CONSTRAINT chk_users_feature_tier CHECK (feature_tier IN ('free', 'premium'))")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_feature_tier ON users(feature_tier)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_users_feature_tier")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_feature_tier")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS feature_tier")
