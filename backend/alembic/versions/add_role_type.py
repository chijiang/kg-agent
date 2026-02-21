"""add role_type column

Revision ID: add_role_type
Revises: 41880421d374
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_role_type"
down_revision = "41880421d374"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column("role_type", sa.String(20), nullable=False, server_default="system"),
    )


def downgrade() -> None:
    op.drop_column("roles", "role_type")
