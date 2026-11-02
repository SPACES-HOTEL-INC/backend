"""add receptionist to userrole enum

Revision ID: 9c1f7d1b2a5b
Revises: f3c2a9a0e7d1
Create Date: 2026-11-02

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '9c1f7d1b2a5b'
down_revision = 'f3c2a9a0e7d1'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='userrole' AND e.enumlabel='RECEPTIONIST') THEN ALTER TYPE userrole ADD VALUE 'RECEPTIONIST'; END IF; END $$;"
    )


def downgrade():
    # PostgreSQL does not support dropping enum values directly in a simple way.
    pass
