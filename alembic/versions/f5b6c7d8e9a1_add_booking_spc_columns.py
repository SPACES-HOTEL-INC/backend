"""add SPC and check-in columns to bookings

Revision ID: f5b6c7d8e9a1
Revises: a1d08f1d0b48
Create Date: 2026-11-21
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f5b6c7d8e9a1"
down_revision: Union[str, Sequence[str], None] = "a1d08f1d0b48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS spc_code VARCHAR(32);")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMP WITH TIME ZONE;")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_bookings_spc_code ON bookings (spc_code);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_bookings_spc_code;")
    op.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS checked_in_at;")
    op.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS spc_code;")
