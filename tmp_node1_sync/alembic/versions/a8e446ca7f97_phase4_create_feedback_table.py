"""phase4_create_feedback_table

Revision ID: a8e446ca7f97
Revises: 20260117_sbb2
Create Date: 2026-01-18 00:42:48.676732

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8e446ca7f97'
down_revision = '20260117_sbb2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'memory_feedback',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('memory_id', sa.UUID(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),  # -1 to 1
        sa.Column('weights_snapshot', sa.JSON(), nullable=True),  # Snapshot of alpha, beta, gamma during query
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_feedback_tenant_memory', 'memory_feedback', ['tenant_id', 'memory_id'])

def downgrade():
    op.drop_table('memory_feedback')
