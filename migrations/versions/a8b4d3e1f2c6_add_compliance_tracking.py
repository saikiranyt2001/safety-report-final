"""add compliance tracking tables

Revision ID: a8b4d3e1f2c6
Revises: e6c1f7b2a4d8
Create Date: 2026-03-13 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a8b4d3e1f2c6'
down_revision: Union[str, Sequence[str], None] = 'e6c1f7b2a4d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'compliance_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('regulation_source', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_compliance_rules_id', 'compliance_rules', ['id'], unique=False)

    op.create_table(
        'compliance_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('checked_by_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('evidence', sa.String(), nullable=True),
        sa.Column('recommended_action', sa.String(), nullable=True),
        sa.Column('maintenance_task_id', sa.Integer(), nullable=True),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['checked_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['maintenance_task_id'], ['hazard_tasks.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['rule_id'], ['compliance_rules.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_compliance_checks_id', 'compliance_checks', ['id'], unique=False)
    op.create_index('ix_compliance_checks_rule_id', 'compliance_checks', ['rule_id'], unique=False)
    op.create_index('ix_compliance_checks_project_id', 'compliance_checks', ['project_id'], unique=False)
    op.create_index('ix_compliance_checks_checked_at', 'compliance_checks', ['checked_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_compliance_checks_checked_at', table_name='compliance_checks')
    op.drop_index('ix_compliance_checks_project_id', table_name='compliance_checks')
    op.drop_index('ix_compliance_checks_rule_id', table_name='compliance_checks')
    op.drop_index('ix_compliance_checks_id', table_name='compliance_checks')
    op.drop_table('compliance_checks')

    op.drop_index('ix_compliance_rules_id', table_name='compliance_rules')
    op.drop_table('compliance_rules')
