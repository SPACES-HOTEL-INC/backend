"""add check_in and check_out columns to bookings

Revision ID: 13d3cbbc0374
Revises: b0dcf38332ac
Create Date: 2026-08-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13d3cbbc0374'
down_revision: Union[str, None] = 'b0dcf38332ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS check_in TIMESTAMP WITH TIME ZONE;")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS check_out TIMESTAMP WITH TIME ZONE;")


def downgrade() -> None:
    op.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS check_in;")
    op.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS check_out;")