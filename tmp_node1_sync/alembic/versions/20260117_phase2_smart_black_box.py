"""Phase 2: Smart Black Box extension

Adds info_class and governance columns to memories table to support
ISO 27000 information classification and ISO 42001 governance metadata.

Revision ID: 20260117_sbb2
Revises: 20260105_phase6_cleanup
Create Date: 2026-01-17 19:30:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '20260117_sbb2'
down_revision = '20260105_phase6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add info_class column
    op.add_column('memories', sa.Column('info_class', sa.String(length=50), nullable=False, server_default='internal'))

    # Add governance column (JSONB)
    op.add_column('memories', sa.Column('governance', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))

    # Add indexes for better auditing and performance
    op.create_index('idx_memories_info_class', 'memories', ['info_class'])
    op.create_index('idx_memories_governance', 'memories', ['governance'], postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('idx_memories_governance', table_name='memories')
    op.drop_index('idx_memories_info_class', table_name='memories')
    op.drop_column('memories', 'governance')
    op.drop_column('memories', 'info_class')
