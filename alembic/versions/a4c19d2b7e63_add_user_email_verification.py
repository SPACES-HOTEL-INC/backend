"""add email OTP verification fields to users

Revision ID: a4c19d2b7e63
Revises: fix_owner_and_total_price
Create Date: 2026-09-29

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a4c19d2b7e63'
down_revision: Union[str, None] = 'fix_owner_and_total_price'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_code VARCHAR(64);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMPTZ;")

    # Accounts that predate OTP verification are grandfathered in as verified so
    # the new login guard does not lock out existing users.
    op.execute("UPDATE users SET is_verified = TRUE WHERE is_verified = FALSE;")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS otp_expires_at;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS otp_code;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_verified;")
