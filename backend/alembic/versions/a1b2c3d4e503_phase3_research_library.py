"""phase 3: research library (metadata only, no files)

Revision ID: a1b2c3d4e503
Revises: a1b2c3d4e502
Create Date: 2026-11-06 13:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e503"
down_revision = "a1b2c3d4e502"
branch_labels = None
depends_on = None


def _ts(name, nullable=False):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "research_papers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("authors", postgresql.ARRAY(sa.String(length=200)), server_default="{}", nullable=False),
        sa.Column("abstract", sa.Text(), server_default="", nullable=False),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("venue", sa.String(length=300), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("keywords", postgresql.ARRAY(sa.String(length=100)), server_default="{}", nullable=False),
        sa.Column("added_by", sa.UUID(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.CheckConstraint(
            "publication_year IS NULL OR publication_year BETWEEN 1800 AND 2200",
            name="ck_research_papers_year",
        ),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_research_papers_doi_lower",
        "research_papers",
        [sa.literal_column("lower(doi)")],
        unique=True,
        postgresql_where=sa.text("doi IS NOT NULL"),
    )
    op.create_index("ix_research_papers_publication_year", "research_papers", ["publication_year"])
    op.create_index("ix_research_papers_authors", "research_papers", ["authors"], postgresql_using="gin")
    op.create_index("ix_research_papers_keywords", "research_papers", ["keywords"], postgresql_using="gin")

    op.create_table(
        "project_papers",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("paper_id", sa.UUID(), nullable=False),
        sa.Column("added_by", sa.UUID(), nullable=True),
        _ts("added_at"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["research_papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("project_id", "paper_id"),
    )
    op.create_index("ix_project_papers_paper_id", "project_papers", ["paper_id"])

    op.create_table(
        "paper_reading_progress",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("paper_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="not_started", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.CheckConstraint(
            "status IN ('not_started', 'reading', 'completed')",
            name="ck_paper_reading_progress_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["research_papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "paper_id",
            "project_id",
            name="uq_paper_reading_progress_user_paper_project",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index("ix_paper_reading_progress_paper_id", "paper_reading_progress", ["paper_id"])
    op.create_index("ix_paper_reading_progress_project_id", "paper_reading_progress", ["project_id"])

    op.create_table(
        "research_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("paper_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["research_papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_notes_user_paper", "research_notes", ["user_id", "paper_id"])


def downgrade() -> None:
    op.drop_table("research_notes")
    op.drop_table("paper_reading_progress")
    op.drop_table("project_papers")
    op.drop_index("uq_research_papers_doi_lower", table_name="research_papers")
    op.drop_table("research_papers")
