"""add hotel_id to users for receptionist scoping

Revision ID: d06cb10d2b55
Revises: 9c1f7d1b2a5b
Create Date: 2026-11-02

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd06cb10d2b55'
down_revision = '9c1f7d1b2a5b'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS hotel_id UUID;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_hotel_id ON users (hotel_id);")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_users_hotel_id_users'
            ) THEN
                ALTER TABLE users
                ADD CONSTRAINT fk_users_hotel_id_users
                FOREIGN KEY (hotel_id) REFERENCES users(id);
            END IF;
        END $$;
        """
    )


def downgrade():
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_hotel_id_users') THEN ALTER TABLE users DROP CONSTRAINT fk_users_hotel_id_users; END IF; END $$;"
    )
    op.execute("DROP INDEX IF EXISTS ix_users_hotel_id;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS hotel_id;")
