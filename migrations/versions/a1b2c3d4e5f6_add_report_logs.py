"""add report_logs table

Revision ID: a1b2c3d4e5f6
Revises: 90489408fe07
Create Date: 2026-07-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '90489408fe07'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('report_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('report_type', sa.String(length=50), nullable=False),
    sa.Column('export_format', sa.String(length=20), nullable=False),
    sa.Column('generated_by_id', sa.Integer(), nullable=False),
    sa.Column('generated_at', sa.DateTime(), nullable=True),
    sa.Column('filters_json', sa.Text(), nullable=True),
    sa.Column('district_scope', sa.String(length=100), nullable=True),
    sa.Column('row_count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['generated_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('report_logs')
