"""create knowledge governance schema

Revision ID: 20260720_knowledge_registry
Revises: 20260720_mesh_security
Create Date: 2026-07-20 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260720_knowledge_registry'
down_revision = '20260720_mesh_security'
branch_labels = None
depends_on = None


def upgrade() -> None:
    knowledge_class_enum = postgresql.ENUM(
        "normative", "architectural", "operational", "empirical", "episodic", "external",
        name="knowledge_class_enum",
        create_type=False,
    )
    authority_level_enum = postgresql.ENUM(
        "canonical", "approved", "observed", "inferred", "untrusted",
        name="authority_level_enum",
        create_type=False,
    )
    source_type_enum = postgresql.ENUM(
        "git", "openapi", "json-schema", "database", "api", "file", "test",
        name="knowledge_source_type_enum",
        create_type=False,
    )
    revision_status_enum = postgresql.ENUM(
        "active", "superseded", "revoked", "expired",
        name="knowledge_revision_status_enum",
        create_type=False,
    )
    payload_storage_enum = postgresql.ENUM(
        "postgres", "object_store",
        name="knowledge_payload_storage_enum",
        create_type=False,
    )
    outbox_status_enum = postgresql.ENUM(
        "pending", "processing", "published", "failed", "dead",
        name="governance_outbox_status_enum",
        create_type=False,
    )

    for enum in (
        knowledge_class_enum,
        authority_level_enum,
        source_type_enum,
        revision_status_enum,
        payload_storage_enum,
        outbox_status_enum,
    ):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "rae_knowledge_registry",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_id", sa.String(255), nullable=False),
        sa.Column("knowledge_class", knowledge_class_enum, nullable=False),
        sa.Column("owner", sa.String(100), nullable=False),
        sa.Column(
            "scope", postgresql.ARRAY(sa.String(255)),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column(
            "generation", sa.BigInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE', name='fk_rae_knowledge_registry_tenant'),
        sa.UniqueConstraint(
            "tenant_id", "knowledge_id",
            name="uq_rae_knowledge_registry_tenant_knowledge",
        ),
        sa.CheckConstraint(
            "length(trim(knowledge_id)) > 0",
            name="ck_rae_knowledge_registry_knowledge_id_not_empty",
        ),
        sa.CheckConstraint(
            "length(trim(owner)) > 0",
            name="ck_rae_knowledge_registry_owner_not_empty",
        ),
        sa.CheckConstraint(
            "generation > 0",
            name="ck_rae_knowledge_registry_generation_positive",
        ),
    )

    op.create_index(
        "ix_rae_knowledge_registry_class",
        "rae_knowledge_registry",
        ["tenant_id", "knowledge_class"],
    )

    op.create_table(
        "rae_knowledge_revisions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "registry_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "rae_knowledge_registry.id",
                ondelete="CASCADE",
                name="fk_rae_revision_registry",
            ),
            nullable=False,
        ),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("authority_level", authority_level_enum, nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("source_ref", sa.String(2048), nullable=False),
        sa.Column("version", sa.String(255), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=False),
        sa.Column(
            "content_size_bytes", sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "metadata", postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", revision_status_enum,
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "registry_id", "revision_no",
            name="uq_rae_revision_registry_revision_no",
        ),
        sa.UniqueConstraint(
            "registry_id", "checksum",
            name="uq_rae_revision_registry_checksum",
        ),
        sa.CheckConstraint(
            "checksum ~ '^[0-9a-f]{64}$'",
            name="ck_rae_revision_checksum_sha256",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from",
            name="ck_rae_revision_valid_range",
        ),
        sa.CheckConstraint(
            "content_size_bytes >= 0",
            name="ck_rae_revision_content_size_non_negative",
        ),
    )

    op.create_index(
        "ix_rae_revision_registry_status",
        "rae_knowledge_revisions",
        ["registry_id", "status"],
    )
    op.create_index(
        "ix_rae_revision_validity",
        "rae_knowledge_revisions",
        ["valid_from", "valid_until"],
    )
    op.create_index(
        "uq_rae_revision_single_active",
        "rae_knowledge_revisions",
        ["registry_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "rae_knowledge_revision_payloads",
        sa.Column(
            "revision_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "rae_knowledge_revisions.id",
                ondelete="CASCADE",
                name="fk_rae_payload_revision",
            ),
            primary_key=True,
        ),
        sa.Column("storage_kind", payload_storage_enum, nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("content_encoding", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.BYTEA(), nullable=True),
        sa.Column("object_uri", sa.String(2048), nullable=True),
        sa.Column("payload_checksum", sa.String(64), nullable=False),
        sa.Column("payload_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "payload_checksum ~ '^[0-9a-f]{64}$'",
            name="ck_rae_payload_checksum_sha256",
        ),
        sa.CheckConstraint(
            "payload_size_bytes >= 0",
            name="ck_rae_payload_size_non_negative",
        ),
        sa.CheckConstraint(
            """
            (storage_kind = 'postgres' AND payload IS NOT NULL AND object_uri IS NULL)
            OR
            (storage_kind = 'object_store' AND payload IS NULL AND object_uri IS NOT NULL)
            """,
            name="ck_rae_payload_storage_consistency",
        ),
    )

    op.create_table(
        "rae_knowledge_supersedes",
        sa.Column(
            "superseding_revision_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "rae_knowledge_revisions.id",
                ondelete="CASCADE",
                name="fk_rae_supersedes_newer_revision",
            ),
            nullable=False,
        ),
        sa.Column(
            "superseded_revision_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "rae_knowledge_revisions.id",
                ondelete="RESTRICT",
                name="fk_rae_supersedes_older_revision",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "superseding_revision_id",
            "superseded_revision_id",
            name="pk_rae_knowledge_supersedes",
        ),
        sa.CheckConstraint(
            "superseding_revision_id <> superseded_revision_id",
            name="ck_rae_knowledge_supersedes_not_self",
        ),
    )

    op.create_table(
        "rae_governance_audit_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stream_id", sa.String(255), nullable=False),
        sa.Column("sequence_no", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("subject_ref", sa.String(2048), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("previous_event_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE', name='fk_rae_governance_audit_events_tenant'),
        sa.UniqueConstraint(
            "tenant_id", "stream_id", "sequence_no",
            name="uq_rae_audit_stream_sequence",
        ),
        sa.CheckConstraint(
            "event_hash ~ '^[0-9a-f]{64}$'",
            name="ck_rae_audit_event_hash_sha256",
        ),
    )

    op.create_index(
        "ix_rae_audit_tenant_created",
        "rae_governance_audit_events",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_rae_audit_stream_sequence",
        "rae_governance_audit_events",
        ["tenant_id", "stream_id", "sequence_no"],
    )

    op.create_table(
        "rae_governance_outbox",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_ref", sa.String(2048), nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", outbox_status_enum,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE', name='fk_rae_governance_outbox_tenant'),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_rae_outbox_attempts_non_negative",
        ),
    )

    op.create_index(
        "ix_rae_outbox_dispatch",
        "rae_governance_outbox",
        ["status", "available_at", "created_at"],
        postgresql_where=sa.text("status IN ('pending', 'failed')"),
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION rae_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_rae_knowledge_registry_updated_at
        BEFORE UPDATE ON rae_knowledge_registry
        FOR EACH ROW EXECUTE FUNCTION rae_set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_rae_knowledge_registry_updated_at "
        "ON rae_knowledge_registry"
    )
    op.execute("DROP FUNCTION IF EXISTS rae_set_updated_at()")
    op.drop_table("rae_governance_outbox")
    op.drop_table("rae_governance_audit_events")
    op.drop_table("rae_knowledge_supersedes")
    op.drop_table("rae_knowledge_revision_payloads")
    op.drop_index(
        "uq_rae_revision_single_active",
        table_name="rae_knowledge_revisions",
    )
    op.drop_table("rae_knowledge_revisions")
    op.drop_table("rae_knowledge_registry")

    op.execute("DROP TYPE IF EXISTS governance_outbox_status_enum")
    op.execute("DROP TYPE IF EXISTS knowledge_payload_storage_enum")
    op.execute("DROP TYPE IF EXISTS knowledge_revision_status_enum")
    op.execute("DROP TYPE IF EXISTS knowledge_source_type_enum")
    op.execute("DROP TYPE IF EXISTS authority_level_enum")
    op.execute("DROP TYPE IF EXISTS knowledge_class_enum")
