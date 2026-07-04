"""Phase 5: Performance Indexes

Revision ID: 20260105_phase5
Revises: 20260105_phase4
Create Date: 2026-01-05 20:45:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260105_phase5"
down_revision = "20260105_phase4"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Index on project
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_memories_project' AND n.nspname = 'public') THEN
                CREATE INDEX idx_memories_project ON memories (project);
            END IF;
        END $$;
    """
    )

    # 2. Index on session_id
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_memories_session_id' AND n.nspname = 'public') THEN
                CREATE INDEX idx_memories_session_id ON memories (session_id);
            END IF;
        END $$;
    """
    )

    # 3. Index on source
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_memories_source' AND n.nspname = 'public') THEN
                CREATE INDEX idx_memories_source ON memories (source);
            END IF;
        END $$;
    """
    )

    # 4. Composite Index for Dashboard Time-Range queries by Project
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'idx_memories_project_created_at' AND n.nspname = 'public') THEN
                CREATE INDEX idx_memories_project_created_at ON memories (project, created_at);
            END IF;
        END $$;
    """
    )


def downgrade():
    op.drop_index("idx_memories_project_created_at", table_name="memories")
    op.drop_index("idx_memories_source", table_name="memories")
    op.drop_index("idx_memories_session_id", table_name="memories")
    op.drop_index("idx_memories_project", table_name="memories")
