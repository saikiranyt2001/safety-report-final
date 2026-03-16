"""add structured inspection fields

Revision ID: 8f1e2d3c4b5a
Revises: f9a2b6c4d8e1
Create Date: 2026-03-16 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f1e2d3c4b5a"
down_revision: Union[str, Sequence[str], None] = "f9a2b6c4d8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("inspection_templates", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("json_schema", sa.JSON(), nullable=True))

    with op.batch_alter_table("inspection_questions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("question_code", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("section_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("risk_level", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("question_type", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("inspection_questions", schema=None) as batch_op:
        batch_op.drop_column("question_type")
        batch_op.drop_column("risk_level")
        batch_op.drop_column("section_name")
        batch_op.drop_column("question_code")

    with op.batch_alter_table("inspection_templates", schema=None) as batch_op:
        batch_op.drop_column("json_schema")
        batch_op.drop_column("category")
