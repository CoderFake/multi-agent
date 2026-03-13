"""add_is_public_to_cms_agent

Revision ID: d1a2b3c4e5f6
Revises: cedb00424a33
Create Date: 2026-03-13 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1a2b3c4e5f6'
down_revision: Union[str, None] = 'cedb00424a33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cms_agent', sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('cms_agent', 'is_public')
