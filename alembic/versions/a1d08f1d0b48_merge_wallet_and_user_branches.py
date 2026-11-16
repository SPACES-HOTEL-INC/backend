"""merge multiple heads and add wallet columns to properties

Revision ID: a1d08f1d0b48
Revises: d4b7c1e90a52, d06cb10d2b55
Create Date: 2026-11-16

This merge keeps the existing schema history intact while adding the wallet
fields already used by the application model. Column additions are guarded with
`IF NOT EXISTS` so they are safe to replay on a live database without dropping
existing data.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1d08f1d0b48'
down_revision: Union[str, Sequence[str], None] = ('d4b7c1e90a52', 'd06cb10d2b55')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS balance NUMERIC(10, 2) DEFAULT 0.00;")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS pending_balance NUMERIC(10, 2) DEFAULT 0.00;")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS bank_details JSONB;")


def downgrade() -> None:
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS bank_details;")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS pending_balance;")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS balance;")
