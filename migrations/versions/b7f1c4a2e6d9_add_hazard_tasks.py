"""add hazard_tasks table

Revision ID: b7f1c4a2e6d9
Revises: a3c5e8b1d9f2
Create Date: 2026-03-13 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7f1c4a2e6d9'
down_revision: Union[str, Sequence[str], None] = 'a3c5e8b1d9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'hazard_tasks',
        sa.Column('id',             sa.Integer(),  nullable=False),
        sa.Column('title',          sa.String(),   nullable=False),
        sa.Column('description',    sa.String(),   nullable=True),
        sa.Column('hazard_type',    sa.String(),   nullable=True),
        sa.Column('priority',
                  sa.Enum('low', 'medium', 'high', 'critical', name='taskpriorityenum'),
                  nullable=False),
        sa.Column('status',
                  sa.Enum('open', 'in_progress', 'resolved', 'closed', name='taskstatusenum'),
                  nullable=False),
        sa.Column('assigned_to_id', sa.Integer(),  nullable=True),
        sa.Column('created_by_id',  sa.Integer(),  nullable=True),
        sa.Column('project_id',     sa.Integer(),  nullable=True),
        sa.Column('deadline',       sa.DateTime(), nullable=True),
        sa.Column('resolved_at',    sa.DateTime(), nullable=True),
        sa.Column('proof_notes',    sa.String(),   nullable=True),
        sa.Column('created_at',     sa.DateTime(), nullable=True),
        sa.Column('updated_at',     sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by_id'],  ['users.id']),
        sa.ForeignKeyConstraint(['project_id'],     ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_hazard_tasks_id',           'hazard_tasks', ['id'],           unique=False)
    op.create_index('ix_hazard_tasks_assigned_to',  'hazard_tasks', ['assigned_to_id'], unique=False)
    op.create_index('ix_hazard_tasks_project_id',   'hazard_tasks', ['project_id'],   unique=False)
    op.create_index('ix_hazard_tasks_created_at',   'hazard_tasks', ['created_at'],   unique=False)


def downgrade() -> None:
    op.drop_index('ix_hazard_tasks_created_at',  table_name='hazard_tasks')
    op.drop_index('ix_hazard_tasks_project_id',  table_name='hazard_tasks')
    op.drop_index('ix_hazard_tasks_assigned_to', table_name='hazard_tasks')
    op.drop_index('ix_hazard_tasks_id',          table_name='hazard_tasks')
    op.drop_table('hazard_tasks')
    op.execute("DROP TYPE IF EXISTS taskstatusenum")
    op.execute("DROP TYPE IF EXISTS taskpriorityenum")
