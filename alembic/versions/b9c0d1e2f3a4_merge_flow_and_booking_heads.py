"""Merge the flow-publication and booking-uniqueness migration heads."""
from typing import Sequence, Union


revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = ("a8b9c0d1e2f3", "d0e1f2a3b4c5")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
