"""phase 1: user moderation metadata and audit logs

Revision ID: a1b2c3d4e501
Revises: seed_global_roles
Create Date: 2026-11-06 12:00:00

Additive only: new nullable columns on users and a new audit_logs table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e501"
down_revision = "seed_global_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("rejected_by", sa.UUID(), nullable=True))
    op.add_column("users", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("suspended_by", sa.UUID(), nullable=True))
    op.add_column("users", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_users_rejected_by", "users", "users", ["rejected_by"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_users_suspended_by", "users", "users", ["suspended_by"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_users_account_status", "users", ["account_status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # Audit records are append-only.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prism_audit_logs_immutable()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prism_audit_logs_immutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prism_audit_logs_immutable()")
    op.drop_table("audit_logs")
    op.drop_index("ix_users_account_status", table_name="users")
    op.drop_constraint("fk_users_suspended_by", "users", type_="foreignkey")
    op.drop_constraint("fk_users_rejected_by", "users", type_="foreignkey")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "suspended_at")
    op.drop_column("users", "suspended_by")
    op.drop_column("users", "rejected_at")
    op.drop_column("users", "rejected_by")
