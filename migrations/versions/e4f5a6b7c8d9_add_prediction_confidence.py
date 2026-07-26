"""add prediction_confidence to water_points

Revision ID: e4f5a6b7c8d9
Revises: drop_maintenance_visits
Create Date: 2026-07-26 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4f5a6b7c8d9'
down_revision = 'drop_maintenance_visits'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('water_points', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prediction_confidence', sa.String(length=10), nullable=True))


def downgrade():
    with op.batch_alter_table('water_points', schema=None) as batch_op:
        batch_op.drop_column('prediction_confidence')
