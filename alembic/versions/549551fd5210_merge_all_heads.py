"""merge_all_heads

Revision ID: 549551fd5210
Revises: b2c3d4e5f6g7, e6f7g8h9i0j1, z1b2c3d4e5f6
Create Date: 2026-05-04 23:52:05.007277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '549551fd5210'
down_revision: Union[str, Sequence[str], None] = ('b2c3d4e5f6g7', 'e6f7g8h9i0j1', 'z1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
