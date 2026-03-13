"""add multi tenant company scoping

Revision ID: c3f9a1b2d4e5
Revises: a8b4d3e1f2c6
Create Date: 2026-03-13 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f9a1b2d4e5"
down_revision: Union[str, Sequence[str], None] = "a8b4d3e1f2c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_company_id(table_name: str, foreign_key_name: str, index_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(sa.Column("company_id", sa.Integer(), nullable=True))
        batch_op.create_index(index_name, ["company_id"], unique=False)
        batch_op.create_foreign_key(foreign_key_name, "companies", ["company_id"], ["id"])


def _drop_company_id(table_name: str, foreign_key_name: str, index_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(foreign_key_name, type_="foreignkey")
        batch_op.drop_index(index_name)
        batch_op.drop_column("company_id")


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )

    _add_company_id("inspection_templates", "fk_inspection_templates_company_id_companies", "ix_inspection_templates_company_id")
    _add_company_id("inspection_responses", "fk_inspection_responses_company_id_companies", "ix_inspection_responses_company_id")
    _add_company_id("hazard_tasks", "fk_hazard_tasks_company_id_companies", "ix_hazard_tasks_company_id")
    _add_company_id("incidents", "fk_incidents_company_id_companies", "ix_incidents_company_id")
    _add_company_id("training_courses", "fk_training_courses_company_id_companies", "ix_training_courses_company_id")
    _add_company_id("training_records", "fk_training_records_company_id_companies", "ix_training_records_company_id")
    _add_company_id("equipment", "fk_equipment_company_id_companies", "ix_equipment_company_id")
    _add_company_id("equipment_inspections", "fk_equipment_inspections_company_id_companies", "ix_equipment_inspections_company_id")
    _add_company_id("compliance_rules", "fk_compliance_rules_company_id_companies", "ix_compliance_rules_company_id")
    _add_company_id("compliance_checks", "fk_compliance_checks_company_id_companies", "ix_compliance_checks_company_id")
    _add_company_id("activity_logs", "fk_activity_logs_company_id_companies", "ix_activity_logs_company_id")

    op.execute(
        sa.text(
            """
            UPDATE inspection_templates
            SET company_id = (
                SELECT users.company_id
                FROM users
                WHERE users.id = inspection_templates.created_by_id
            )
            WHERE company_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE inspection_responses
            SET company_id = (
                SELECT users.company_id
                FROM users
                WHERE users.id = inspection_responses.answered_by_id
            )
            WHERE company_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE hazard_tasks
            SET company_id = COALESCE(
                (
                    SELECT projects.company_id
                    FROM projects
                    WHERE projects.id = hazard_tasks.project_id
                ),
                (
                    SELECT users.company_id
                    FROM users
                    WHERE users.id = hazard_tasks.created_by_id
                ),
                (
                    SELECT users.company_id
                    FROM users
                    WHERE users.id = hazard_tasks.assigned_to_id
                )
            )
            WHERE company_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE incidents
            SET company_id = COALESCE(
                (
                    SELECT projects.company_id
                    FROM projects
                    WHERE projects.id = incidents.project_id
                ),
                (
                    SELECT users.company_id
                    FROM users
                    WHERE users.id = incidents.reported_by
                )
            )
            WHERE company_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE training_records
            SET company_id = COALESCE(
                (
                    SELECT users.company_id
                    FROM users
                    WHERE users.id = training_records.user_id
                ),
                (
                    SELECT training_courses.company_id
                    FROM training_courses
                    WHERE training_courses.id = training_records.course_id
                )
            )
            WHERE company_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE equipment_inspections
            SET company_id = COALESCE(
                (
                    SELECT equipment.company_id
                    FROM equipment
                    WHERE equipment.id = equipment_inspections.equipment_id
                ),
                (
                    SELECT users.company_id
                    FROM users
                    WHERE users.id = equipment_inspections.inspector_id
                )
            )
            WHERE company_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE compliance_checks
            SET company_id = COALESCE(
                (
                    SELECT compliance_rules.company_id
                    FROM compliance_rules
                    WHERE compliance_rules.id = compliance_checks.rule_id
                ),
                (
                    SELECT projects.company_id
                    FROM projects
                    WHERE projects.id = compliance_checks.project_id
                ),
                (
                    SELECT users.company_id
                    FROM users
                    WHERE users.id = compliance_checks.checked_by_id
                )
            )
            WHERE company_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE activity_logs
            SET company_id = (
                SELECT users.company_id
                FROM users
                WHERE users.id = activity_logs.user_id
            )
            WHERE company_id IS NULL
            """
        )
    )


def downgrade() -> None:
    _drop_company_id("activity_logs", "fk_activity_logs_company_id_companies", "ix_activity_logs_company_id")
    _drop_company_id("compliance_checks", "fk_compliance_checks_company_id_companies", "ix_compliance_checks_company_id")
    _drop_company_id("compliance_rules", "fk_compliance_rules_company_id_companies", "ix_compliance_rules_company_id")
    _drop_company_id("equipment_inspections", "fk_equipment_inspections_company_id_companies", "ix_equipment_inspections_company_id")
    _drop_company_id("equipment", "fk_equipment_company_id_companies", "ix_equipment_company_id")
    _drop_company_id("training_records", "fk_training_records_company_id_companies", "ix_training_records_company_id")
    _drop_company_id("training_courses", "fk_training_courses_company_id_companies", "ix_training_courses_company_id")
    _drop_company_id("incidents", "fk_incidents_company_id_companies", "ix_incidents_company_id")
    _drop_company_id("hazard_tasks", "fk_hazard_tasks_company_id_companies", "ix_hazard_tasks_company_id")
    _drop_company_id("inspection_responses", "fk_inspection_responses_company_id_companies", "ix_inspection_responses_company_id")
    _drop_company_id("inspection_templates", "fk_inspection_templates_company_id_companies", "ix_inspection_templates_company_id")

    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("created_at")