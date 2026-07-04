"""normalize_layer_names

Revision ID: 35c0e303d4c4
Revises: f2g3h4i5j6k7
Create Date: 2026-01-04 13:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "35c0e303d4c4"
down_revision = "000000000000"
branch_labels = None
depends_on = None


def upgrade():
    # Normalize legacy short layer codes to full standard names
    op.execute("UPDATE memories SET layer = 'episodic' WHERE layer = 'em'")
    op.execute(
        "UPDATE memories SET layer = 'working' WHERE layer = 'stm' OR layer = 'wm'"
    )
    op.execute(
        "UPDATE memories SET layer = 'semantic' WHERE layer = 'ltm' OR layer = 'sm'"
    )
    op.execute("UPDATE memories SET layer = 'reflective' WHERE layer = 'rm'")


def downgrade():
    # We stick to the new full names as standard
    pass
