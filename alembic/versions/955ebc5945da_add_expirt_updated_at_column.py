"""add expirt_updated_at column

Revision ID: 955ebc5945da
Revises: 8127e1334f77
Create Date: 2026-08-02 13:18:52.088611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '955ebc5945da'
down_revision: Union[str, Sequence[str], None] = '8127e1334f77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "urls",
        sa.Column(
            "expiry_updated_at",
            sa.DateTime(timezone=True),
            nullable=False
        )
    )    # ### end Alembic commands ###


def downgrade():
    op.drop_column("urls", "expiry_updated_at")
    # ### end Alembic commands ###
