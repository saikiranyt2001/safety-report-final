"""add incidents and investigations tables

Revision ID: f4d8c2a9e1b7
Revises: b7f1c4a2e6d9
Create Date: 2026-03-13 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4d8c2a9e1b7'
down_revision: Union[str, Sequence[str], None] = 'b7f1c4a2e6d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('reported_by', sa.Integer(), nullable=True),
        sa.Column('incident_type', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical', name='incidentseverityenum'), nullable=False),
        sa.Column('status', sa.Enum('open', 'investigating', 'closed', name='incidentstatusenum'), nullable=False),
        sa.Column('immediate_action', sa.String(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['reported_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_incidents_id', 'incidents', ['id'], unique=False)
    op.create_index('ix_incidents_project_id', 'incidents', ['project_id'], unique=False)
    op.create_index('ix_incidents_reported_by', 'incidents', ['reported_by'], unique=False)
    op.create_index('ix_incidents_created_at', 'incidents', ['created_at'], unique=False)

    op.create_table(
        'incident_investigations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('root_cause', sa.String(), nullable=False),
        sa.Column('corrective_action', sa.String(), nullable=False),
        sa.Column('contributing_factor', sa.String(), nullable=True),
        sa.Column('investigated_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.ForeignKeyConstraint(['investigated_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('incident_id'),
    )
    op.create_index('ix_incident_investigations_id', 'incident_investigations', ['id'], unique=False)
    op.create_index('ix_incident_investigations_incident_id', 'incident_investigations', ['incident_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_incident_investigations_incident_id', table_name='incident_investigations')
    op.drop_index('ix_incident_investigations_id', table_name='incident_investigations')
    op.drop_table('incident_investigations')

    op.drop_index('ix_incidents_created_at', table_name='incidents')
    op.drop_index('ix_incidents_reported_by', table_name='incidents')
    op.drop_index('ix_incidents_project_id', table_name='incidents')
    op.drop_index('ix_incidents_id', table_name='incidents')
    op.drop_table('incidents')

    op.execute("DROP TYPE IF EXISTS incidentstatusenum")
    op.execute("DROP TYPE IF EXISTS incidentseverityenum")
