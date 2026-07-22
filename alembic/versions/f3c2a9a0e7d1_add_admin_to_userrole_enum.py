"""add admin to userrole enum

Revision ID: f3c2a9a0e7d1
Revises: be89f18b5850
Create Date: 2026-07-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3c2a9a0e7d1'
down_revision = '0c7b22725283'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='userrole' AND e.enumlabel='ADMIN') THEN ALTER TYPE userrole ADD VALUE 'ADMIN'; END IF; END $$;")


def downgrade():
    # PostgreSQL does not support dropping enum values directly in a simple way.
    pass
