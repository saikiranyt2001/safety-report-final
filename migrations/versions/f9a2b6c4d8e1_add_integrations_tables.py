"""add integrations tables

Revision ID: f9a2b6c4d8e1
Revises: c3f9a1b2d4e5
Create Date: 2026-03-14 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9a2b6c4d8e1"
down_revision: Union[str, Sequence[str], None] = "c3f9a1b2d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


integration_type_enum = sa.Enum("email", "slack", "teams", "webhook", name="integrationtypeenum")


def upgrade() -> None:
    integration_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "integration_endpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("integration_type", integration_type_enum, nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("secret", sa.String(), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_endpoints_id", "integration_endpoints", ["id"], unique=False)
    op.create_index("ix_integration_endpoints_company_id", "integration_endpoints", ["company_id"], unique=False)

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key_prefix", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_id", "api_keys", ["id"], unique=False)
    op.create_index("ix_api_keys_company_id", "api_keys", ["company_id"], unique=False)
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
    op.drop_index("ix_api_keys_company_id", table_name="api_keys")
    op.drop_index("ix_api_keys_id", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index("ix_integration_endpoints_company_id", table_name="integration_endpoints")
    op.drop_index("ix_integration_endpoints_id", table_name="integration_endpoints")
    op.drop_table("integration_endpoints")

    integration_type_enum.drop(op.get_bind(), checkfirst=True)
