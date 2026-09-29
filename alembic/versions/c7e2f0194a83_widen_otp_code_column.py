"""widen users.otp_code to hold an HMAC-SHA256 digest

The column was created as VARCHAR(6) to match the OTP itself, but the value
stored is a 64-character hex digest, so writes fail with
StringDataRightTruncationError. Widening is lossless.

Revision ID: c7e2f0194a83
Revises: a4c19d2b7e63
Create Date: 2026-09-29

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'c7e2f0194a83'
down_revision: Union[str, None] = 'a4c19d2b7e63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN otp_code TYPE VARCHAR(64);")


def downgrade() -> None:
    # Any unconsumed OTP digest would be truncated here, so clear the column
    # first; the values are unusable at 6 characters either way.
    op.execute("UPDATE users SET otp_code = NULL WHERE otp_code IS NOT NULL;")
    op.execute("ALTER TABLE users ALTER COLUMN otp_code TYPE VARCHAR(6);")
