"""seed predefined global roles

Revision ID: 255b975439a8
Revises: 1702395f628c
Create Date: 2026-11-06 11:37:11.328189

"""
from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision = "seed_global_roles"
down_revision = "1702395f628c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    roles_table = sa.table(
        "roles",
        sa.column("name", sa.String(30)),
    )

    op.bulk_insert(
        roles_table,
        [
            {"name": "Administrator"},
            {"name": "Professor"},
            {"name": "Student"},
            {"name": "Guest"},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE name IN (
                'Administrator',
                'Professor',
                'Student',
                'Guest'
            )
            """
        )
    )