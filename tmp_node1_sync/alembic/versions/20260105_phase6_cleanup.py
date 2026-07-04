"""Phase 6: Cleanup dead columns

Revision ID: 20260105_phase6
Revises: 20260105_phase5
Create Date: 2026-01-05 21:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260105_phase6"
down_revision = "20260105_phase5"
branch_labels = None
depends_on = None


def upgrade():
    # Remove dead column qdrant_point_id safely
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'memories' AND column_name = 'qdrant_point_id') THEN
                ALTER TABLE memories DROP COLUMN qdrant_point_id;
            END IF;
        END $$;
    """
    )


def downgrade():
    # Recreate the column if we rollback
    op.add_column("memories", sa.Column("qdrant_point_id", sa.Text(), nullable=True))
