"""create mesh federation tables

Revision ID: 20260720_mesh_security
Revises: 9ee276de27bb
Create Date: 2026-07-20 07:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20260720_mesh_security'
down_revision = '9ee276de27bb'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create mesh_peers table
    op.create_table(
        'mesh_peers',
        sa.Column('peer_id', sa.String(length=255), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('transport_type', sa.String(length=50), nullable=False),
        sa.Column('endpoint_url', sa.String(length=512), nullable=False),
        sa.Column('encrypted_auth_token', sa.Text(), nullable=True),
        sa.Column('consent_grant_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    # 2. Create mesh_sync_log table
    op.create_table(
        'mesh_sync_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('peer_id', sa.String(length=255), nullable=False),
        sa.Column('memory_id', UUID(as_uuid=True), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['peer_id'], ['mesh_peers.peer_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['memory_id'], ['memories.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('peer_id', 'memory_id', 'status', name='uq_mesh_sync_log_peer_memory_status')
    )


def downgrade():
    op.drop_table('mesh_sync_log')
    op.drop_table('mesh_peers')
