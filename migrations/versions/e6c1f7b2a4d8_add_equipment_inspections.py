"""add equipment and equipment inspections tables

Revision ID: e6c1f7b2a4d8
Revises: d2a7b6c9e4f1
Create Date: 2026-03-13 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6c1f7b2a4d8'
down_revision: Union[str, Sequence[str], None] = 'd2a7b6c9e4f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('serial_number', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('inspection_interval_days', sa.Integer(), nullable=False),
        sa.Column('last_inspection_date', sa.DateTime(), nullable=True),
        sa.Column('next_inspection_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_equipment_id', 'equipment', ['id'], unique=False)
    op.create_index('ix_equipment_next_inspection_date', 'equipment', ['next_inspection_date'], unique=False)

    op.create_table(
        'equipment_inspections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('inspector_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('inspection_date', sa.DateTime(), nullable=False),
        sa.Column('checklist_summary', sa.String(), nullable=True),
        sa.Column('issues_found', sa.String(), nullable=True),
        sa.Column('maintenance_task_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id']),
        sa.ForeignKeyConstraint(['inspector_id'], ['users.id']),
        sa.ForeignKeyConstraint(['maintenance_task_id'], ['hazard_tasks.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_equipment_inspections_id', 'equipment_inspections', ['id'], unique=False)
    op.create_index('ix_equipment_inspections_equipment_id', 'equipment_inspections', ['equipment_id'], unique=False)
    op.create_index('ix_equipment_inspections_inspector_id', 'equipment_inspections', ['inspector_id'], unique=False)
    op.create_index('ix_equipment_inspections_inspection_date', 'equipment_inspections', ['inspection_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_equipment_inspections_inspection_date', table_name='equipment_inspections')
    op.drop_index('ix_equipment_inspections_inspector_id', table_name='equipment_inspections')
    op.drop_index('ix_equipment_inspections_equipment_id', table_name='equipment_inspections')
    op.drop_index('ix_equipment_inspections_id', table_name='equipment_inspections')
    op.drop_table('equipment_inspections')

    op.drop_index('ix_equipment_next_inspection_date', table_name='equipment')
    op.drop_index('ix_equipment_id', table_name='equipment')
    op.drop_table('equipment')
