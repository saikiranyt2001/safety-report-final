"""add training tracking tables

Revision ID: d2a7b6c9e4f1
Revises: f4d8c2a9e1b7
Create Date: 2026-03-13 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2a7b6c9e4f1'
down_revision: Union[str, Sequence[str], None] = 'f4d8c2a9e1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'training_courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('validity_months', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_training_courses_id', 'training_courses', ['id'], unique=False)

    op.create_table(
        'training_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('completed_date', sa.DateTime(), nullable=True),
        sa.Column('expiry_date', sa.DateTime(), nullable=True),
        sa.Column('certificate_ref', sa.String(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['course_id'], ['training_courses.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_training_records_id', 'training_records', ['id'], unique=False)
    op.create_index('ix_training_records_user_id', 'training_records', ['user_id'], unique=False)
    op.create_index('ix_training_records_course_id', 'training_records', ['course_id'], unique=False)
    op.create_index('ix_training_records_assigned_at', 'training_records', ['assigned_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_training_records_assigned_at', table_name='training_records')
    op.drop_index('ix_training_records_course_id', table_name='training_records')
    op.drop_index('ix_training_records_user_id', table_name='training_records')
    op.drop_index('ix_training_records_id', table_name='training_records')
    op.drop_table('training_records')

    op.drop_index('ix_training_courses_id', table_name='training_courses')
    op.drop_table('training_courses')
