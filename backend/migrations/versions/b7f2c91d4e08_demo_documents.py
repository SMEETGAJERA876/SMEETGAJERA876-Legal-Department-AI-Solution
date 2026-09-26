"""demo documents

Revision ID: b7f2c91d4e08
Revises: 81ac85c8cd68
Create Date: 2026-09-26 10:05:11.402913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f2c91d4e08'
down_revision: Union[str, Sequence[str], None] = '81ac85c8cd68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'documents',
        sa.Column('is_demo', sa.Boolean(), server_default='false', nullable=False),
    )
    op.create_index(op.f('ix_documents_is_demo'), 'documents', ['is_demo'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_documents_is_demo'), table_name='documents')
    op.drop_column('documents', 'is_demo')
