"""fix owner_id constraint and add total_price to bookings

Revision ID: fix_owner_and_total_price
Revises: 13d3cbbc0374
Create Date: 2026-08-20

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'fix_owner_and_total_price'
down_revision: Union[str, None] = '13d3cbbc0374'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop unique constraint on host/owner
    op.execute("ALTER TABLE properties DROP CONSTRAINT IF EXISTS properties_owner_id_key;")
    
    # Add total_price column to bookings
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS total_price NUMERIC(10, 2) DEFAULT 0.00;")


def downgrade() -> None:
    op.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS total_price;")
    op.execute("ALTER TABLE properties ADD CONSTRAINT properties_owner_id_key UNIQUE (owner_id);")