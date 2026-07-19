"""remove orphan maintenance_visits table

The maintenance_visits table exists in the database but has no SQLAlchemy
model and no migration creating it. It is not referenced anywhere in the
application code, so it is dropped to keep the schema consistent with the
models.

Revision ID: drop_maintenance_visits
Revises: a1b2c3d4e5f6
Create Date: 2026-07-19 21:04:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "drop_maintenance_visits"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("maintenance_visits")


def downgrade():
    op.create_table(
        "maintenance_visits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("water_point_id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("visit_date", sa.DateTime(), nullable=True),
        sa.Column("issue_found", sa.Text(), nullable=True),
        sa.Column("actions_taken", sa.Text(), nullable=True),
        sa.Column("status_after_visit", sa.String(length=20), nullable=True),
        sa.Column("parts_replaced", sa.Text(), nullable=True),
        sa.Column("cost_estimate", sa.Float(), nullable=True),
        sa.Column("check_in_lat", sa.Float(), nullable=True),
        sa.Column("check_in_lng", sa.Float(), nullable=True),
        sa.Column("check_out_lat", sa.Float(), nullable=True),
        sa.Column("check_out_lng", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["technician_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["water_point_id"], ["water_points.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
