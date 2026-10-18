"""add users.roles so one account can hold multiple roles

Lets an existing hotel account also register as a consumer without a second
row for the same email. `role` remains the primary role; `roles` holds the full
set. Existing rows are backfilled from `role` so behaviour is unchanged until
the next registration.

Revision ID: d4b7c1e90a52
Revises: c7e2f0194a83
Create Date: 2026-10-01

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'd4b7c1e90a52'
down_revision: Union[str, None] = 'c7e2f0194a83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS roles JSONB NOT NULL DEFAULT '[]'::jsonb;")

    # Seed each account with the role it already has. The stored enum value is
    # the uppercase form ('HOTEL'), but UserRole's canonical value is 'host',
    # so translate rather than just lowercasing.
    op.execute(
        """
        UPDATE users
        SET roles = jsonb_build_array(
            CASE lower(role::text)
                WHEN 'hotel' THEN 'host'
                WHEN 'host'  THEN 'host'
                WHEN 'admin' THEN 'admin'
                ELSE 'consumer'
            END
        )
        WHERE roles IS NULL OR roles = '[]'::jsonb;
        """
    )


def downgrade() -> None:
    # Multi-role data cannot be represented in the single `role` column. Keep
    # the most privileged role on each row so no access is silently widened.
    op.execute(
        """
        UPDATE users
        SET role = CASE
            WHEN roles ? 'admin' THEN 'ADMIN'::userrole
            WHEN roles ? 'host' THEN 'HOTEL'::userrole
            ELSE 'CONSUMER'::userrole
        END;
        """
    )
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS roles;")
