"""add_missing_property_columns

Revision ID: b0dcf38332ac
Revises: f3c2a9a0e7d1
Create Date: 2026-07-20 14:22:38.683475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0dcf38332ac'
down_revision: Union[str, None] = 'f3c2a9a0e7d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('properties', sa.Column('description', sa.String(), nullable=True))
    op.add_column('properties', sa.Column('property_type', sa.String(), nullable=True, server_default='hotel'))
    op.add_column('properties', sa.Column('city', sa.String(), nullable=True))
    op.add_column('properties', sa.Column('state', sa.String(), nullable=True))
    op.add_column('properties', sa.Column('country', sa.String(), nullable=True, server_default='Nigeria'))
    op.add_column('properties', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('amenities', sa.JSON(), nullable=True))
    op.add_column('properties', sa.Column('images', sa.JSON(), nullable=True))
    op.add_column('properties', sa.Column('cancellation_policy', sa.String(), nullable=True, server_default='flexible'))
    op.add_column('properties', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('properties', sa.Column('avg_rating', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('properties', sa.Column('total_reviews', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('properties', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')))
    op.add_column('properties', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')))
    op.add_column('properties', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade() -> None:
    op.drop_column('properties', 'is_active')
    op.drop_column('properties', 'updated_at')
    op.drop_column('properties', 'created_at')
    op.drop_column('properties', 'total_reviews')
    op.drop_column('properties', 'avg_rating')
    op.drop_column('properties', 'is_verified')
    op.drop_column('properties', 'cancellation_policy')
    op.drop_column('properties', 'images')
    op.drop_column('properties', 'amenities')
    op.drop_column('properties', 'longitude')
    op.drop_column('properties', 'latitude')
    op.drop_column('properties', 'country')
    op.drop_column('properties', 'state')
    op.drop_column('properties', 'city')
    op.drop_column('properties', 'property_type')
    op.drop_column('properties', 'description')
