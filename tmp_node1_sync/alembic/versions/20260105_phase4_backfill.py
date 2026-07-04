"""Phase 4: Backfill canonical columns from metadata

Revision ID: 20260105_phase4
Revises:
Create Date: 2026-01-05 20:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260105_phase4"
down_revision = "35c0e303d4c4"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Backfill session_id
    op.execute(
        """
        UPDATE memories
        SET session_id = metadata->>'session_id'
        WHERE session_id IS NULL AND metadata->>'session_id' IS NOT NULL
    """
    )

    # 2. Backfill project
    op.execute(
        """
        UPDATE memories
        SET project = metadata->>'project'
        WHERE project IS NULL AND metadata->>'project' IS NOT NULL
    """
    )

    # 3. Backfill source
    op.execute(
        """
        UPDATE memories
        SET source = metadata->>'source'
        WHERE source IS NULL AND metadata->>'source' IS NOT NULL
    """
    )

    # 4. Optional: Backfill memory_type from layer if missing
    # Defaulting to 'text' or mapping based on layer if needed.
    # For now, we leave it as default or explicit.


def downgrade():
    # This is a data migration, usually we don't revert data backfills unless they are destructive.
    # Since we copied data, we can just leave it or set columns to NULL if we really wanted to reverse.
    # But for safety, we do nothing.
    pass
