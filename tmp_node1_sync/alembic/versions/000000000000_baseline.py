"""baseline

Revision ID: 000000000000
Revises:
Create Date: 2026-01-04 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "000000000000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. Memories
    op.create_table(
        "memories",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("importance", sa.Float(), server_default="0.5", nullable=True),
        sa.Column("layer", sa.String(length=50), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=True),
        sa.Column("project", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=True),
        sa.Column(
            "agent_id", sa.String(length=255), server_default="default", nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("memory_type", sa.String(length=50), nullable=True),
        sa.Column("strength", sa.Float(), server_default="1.0", nullable=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        # Assuming pgvector handles 'vector' type via custom type or string/array
        # For simplicity in baseline, we use raw SQL for vector column or omit if not supported by SQLAlchemy directly here
        # But we can use op.execute for specific vector column creation or custom type.
        # Here we use sa.Column('embedding', ... ) with a custom type if defined, or just exec SQL.
        # Using execute for clarity and to ensure 'vector' type usage.
        if_not_exists=True,
    )
    # Add embedding column manually to ensure vector type is used
    op.execute("ALTER TABLE memories ADD COLUMN embedding vector")

    op.create_index("idx_memories_tenant_id", "memories", ["tenant_id"])
    op.create_index("idx_memories_project", "memories", ["project"])
    op.create_index("idx_memories_agent_id", "memories", ["agent_id"])

    # 2. Embeddings
    op.create_table(
        "memory_embeddings",
        sa.Column("memory_id", postgresql.UUID(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("memory_id", "model_name"),
        if_not_exists=True,
    )
    op.execute("ALTER TABLE memory_embeddings ADD COLUMN embedding vector NOT NULL")

    # 3. Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tier", sa.String(length=50), server_default="free", nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column(
            "status", sa.String(length=50), server_default="active", nullable=True
        ),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column(
            "current_memory_count", sa.Integer(), server_default="0", nullable=True
        ),
        sa.Column(
            "current_project_count", sa.Integer(), server_default="0", nullable=True
        ),
        sa.Column("api_calls_today", sa.Integer(), server_default="0", nullable=True),
        sa.Column("subscription_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_end", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    # 4. Roles
    op.create_table(
        "user_tenant_roles",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column(
            "project_ids",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column("assigned_by", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant_role"),
        if_not_exists=True,
    )
    op.create_index("idx_utr_user_id", "user_tenant_roles", ["user_id"])
    op.create_index("idx_utr_tenant_id", "user_tenant_roles", ["tenant_id"])

    # 5. Budgets
    op.create_table(
        "budgets",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("monthly_limit", sa.Float(), nullable=True),
        sa.Column("monthly_usage", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("daily_limit", sa.Float(), nullable=True),
        sa.Column("daily_usage", sa.Float(), server_default="0.0", nullable=False),
        sa.Column(
            "last_usage_at",
            sa.DateTime(),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "project_id", name="uq_tenant_project_budget"),
        if_not_exists=True,
    )

    # 6. Access Logs
    op.create_table(
        "access_logs",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("denial_reason", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("ix_access_logs_tenant_id", "access_logs", ["tenant_id"])
    op.create_index("ix_access_logs_timestamp", "access_logs", ["timestamp"])
    op.create_index("ix_access_logs_user_id", "access_logs", ["user_id"])

    # 7. Token Savings
    op.create_table(
        "token_savings_log",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("predicted_tokens", sa.Integer(), server_default="0", nullable=True),
        sa.Column("real_tokens", sa.Integer(), server_default="0", nullable=True),
        sa.Column("saved_tokens", sa.Integer(), server_default="0", nullable=True),
        sa.Column(
            "estimated_cost_saved_usd", sa.Float(), server_default="0.0", nullable=True
        ),
        sa.Column("savings_type", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    # 8. Knowledge Graph
    op.create_table(
        "knowledge_graph_nodes",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("properties", postgresql.JSONB(), server_default="{}", nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "project_id", "node_id", name="uq_tenant_project_node"
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_kg_nodes_tp", "knowledge_graph_nodes", ["tenant_id", "project_id"]
    )

    op.create_table(
        "knowledge_graph_edges",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("source_node_id", postgresql.UUID(), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(), nullable=False),
        sa.Column("relation", sa.String(), nullable=False),
        sa.Column("properties", postgresql.JSONB(), server_default="{}", nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"], ["knowledge_graph_nodes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"], ["knowledge_graph_nodes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "source_node_id",
            "target_node_id",
            "relation",
            name="uq_kg_edge",
        ),
        if_not_exists=True,
    )
    op.create_index("idx_kg_edges_relation", "knowledge_graph_edges", ["relation"])


def downgrade():
    op.drop_table("knowledge_graph_edges")
    op.drop_table("knowledge_graph_nodes")
    op.drop_table("token_savings_log")
    op.drop_table("access_logs")
    op.drop_table("budgets")
    op.drop_table("user_tenant_roles")
    op.drop_table("tenants")
    op.drop_table("memory_embeddings")
    op.drop_table("memories")
