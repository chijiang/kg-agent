"""rename_name_to_display_name

Revision ID: d7edf8282b68
Revises: add_role_type
Create Date: 2026-02-19 18:09:02.382232

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7edf8282b68"
down_revision: Union[str, Sequence[str], None] = "add_role_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename column 'name' to '_display_name'
    op.alter_column("graph_entities", "name", new_column_name="_display_name")
    # Rename index 'idx_entities_name' to 'idx_entities_display_name'
    op.execute("ALTER INDEX idx_entities_name RENAME TO idx_entities_display_name")


def downgrade() -> None:
    # Rename column '_display_name' back to 'name'
    op.alter_column("graph_entities", "_display_name", new_column_name="name")
    # Rename index back
    op.execute("ALTER INDEX idx_entities_display_name RENAME TO idx_entities_name")
