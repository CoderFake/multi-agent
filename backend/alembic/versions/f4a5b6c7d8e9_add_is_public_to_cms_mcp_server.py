"""add is_public to cms_mcp_server

Revision ID: f4a5b6c7d8e9
Revises: 05ed22ea392c
Create Date: 2026-03-13 19:18:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4a5b6c7d8e9"
down_revision = "05ed22ea392c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cms_mcp_server",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("cms_mcp_server", "is_public")
