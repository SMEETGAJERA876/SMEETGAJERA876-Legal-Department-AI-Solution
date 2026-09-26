"""authenticity

Revision ID: c3d81f60a94b
Revises: b7f2c91d4e08
Create Date: 2026-09-26 13:40:22.115308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d81f60a94b'
down_revision: Union[str, Sequence[str], None] = 'b7f2c91d4e08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('documents', sa.Column('authenticity_verdict', sa.String(length=20), nullable=True))
    op.add_column('documents', sa.Column('authenticity', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(
        op.f('ix_documents_authenticity_verdict'), 'documents', ['authenticity_verdict']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_documents_authenticity_verdict'), table_name='documents')
    op.drop_column('documents', 'authenticity')
    op.drop_column('documents', 'authenticity_verdict')
