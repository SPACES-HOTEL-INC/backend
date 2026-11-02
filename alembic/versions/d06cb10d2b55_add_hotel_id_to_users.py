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
    op.add_column('users', sa.Column('hotel_id', sa.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_users_hotel_id'), 'users', ['hotel_id'], unique=False)
    op.create_foreign_key(
        'fk_users_hotel_id_users',
        'users',
        'users',
        ['hotel_id'],
        ['id'],
    )


def downgrade():
    op.drop_constraint('fk_users_hotel_id_users', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_hotel_id'), table_name='users')
    op.drop_column('users', 'hotel_id')
