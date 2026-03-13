"""add_server_default_to_mcp_created_at

Revision ID: e2f3a4b5c6d7
Revises: d1a2b3c4e5f6
Create Date: 2026-03-13 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1a2b3c4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('cms_mcp_server', 'created_at',
                    server_default=sa.text('now()'),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
    op.alter_column('cms_tool', 'created_at',
                    server_default=sa.text('now()'),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)


def downgrade() -> None:
    op.alter_column('cms_tool', 'created_at',
                    server_default=None,
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
    op.alter_column('cms_mcp_server', 'created_at',
                    server_default=None,
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
