"""add_agent_id_to_group_tool_access

Revision ID: ce07bbeda6d6
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14 00:17:33.779082

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce07bbeda6d6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete existing rows (they lack agent_id and cannot be backfilled)
    op.execute("DELETE FROM cms_group_tool_access")

    op.add_column('cms_group_tool_access', sa.Column('agent_id', sa.UUID(), nullable=False))
    op.create_index(op.f('ix_cms_group_tool_access_agent_id'), 'cms_group_tool_access', ['agent_id'], unique=False)
    op.create_unique_constraint('uq_group_agent_tool_org', 'cms_group_tool_access', ['group_id', 'agent_id', 'tool_id', 'org_id'])
    op.create_foreign_key('fk_group_tool_access_agent', 'cms_group_tool_access', 'cms_agent', ['agent_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint('fk_group_tool_access_agent', 'cms_group_tool_access', type_='foreignkey')
    op.drop_constraint('uq_group_agent_tool_org', 'cms_group_tool_access', type_='unique')
    op.drop_index(op.f('ix_cms_group_tool_access_agent_id'), table_name='cms_group_tool_access')
    op.drop_column('cms_group_tool_access', 'agent_id')
