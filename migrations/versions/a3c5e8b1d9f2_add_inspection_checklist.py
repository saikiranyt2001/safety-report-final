"""add inspection checklist tables

Revision ID: a3c5e8b1d9f2
Revises: 9f2b7d1a4c3e
Create Date: 2026-03-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c5e8b1d9f2'
down_revision: Union[str, Sequence[str], None] = '9f2b7d1a4c3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'inspection_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inspection_templates_id'), 'inspection_templates', ['id'], unique=False)

    op.create_table(
        'inspection_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['inspection_templates.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inspection_questions_id'), 'inspection_questions', ['id'], unique=False)
    op.create_index(op.f('ix_inspection_questions_template_id'), 'inspection_questions', ['template_id'], unique=False)

    op.create_table(
        'inspection_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answered_by_id', sa.Integer(), nullable=True),
        sa.Column('answer', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['answered_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['question_id'], ['inspection_questions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inspection_responses_id'), 'inspection_responses', ['id'], unique=False)
    op.create_index(op.f('ix_inspection_responses_question_id'), 'inspection_responses', ['question_id'], unique=False)
    op.create_index(op.f('ix_inspection_responses_submitted_at'), 'inspection_responses', ['submitted_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_inspection_responses_submitted_at'), table_name='inspection_responses')
    op.drop_index(op.f('ix_inspection_responses_question_id'), table_name='inspection_responses')
    op.drop_index(op.f('ix_inspection_responses_id'), table_name='inspection_responses')
    op.drop_table('inspection_responses')

    op.drop_index(op.f('ix_inspection_questions_template_id'), table_name='inspection_questions')
    op.drop_index(op.f('ix_inspection_questions_id'), table_name='inspection_questions')
    op.drop_table('inspection_questions')

    op.drop_index(op.f('ix_inspection_templates_id'), table_name='inspection_templates')
    op.drop_table('inspection_templates')
