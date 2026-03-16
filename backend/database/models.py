
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, JSON
from sqlalchemy.orm import relationship
from datetime import UTC, datetime
from .database import Base
import enum

from .tenant_mixin import TenantMixin


def utc_now() -> datetime:
    return datetime.now(UTC)
# -----------------------------
# User Roles
# -----------------------------
class RoleEnum(enum.Enum):
    admin = "admin"
    manager = "manager"
    worker = "worker"


# -----------------------------
# Company
# -----------------------------
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    users = relationship(
        "User",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    projects = relationship(
        "Project",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    usage_records = relationship(
        "Usage",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Company {self.name}>"


# -----------------------------
# User
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(Enum(RoleEnum), default=RoleEnum.worker, nullable=False)

    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    company = relationship("Company", back_populates="users")

    usage = relationship(
        "Usage",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    activity_logs = relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    settings = relationship(
        "UserSettings",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    account_state = relationship(
        "UserAccountState",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self):
        return f"<User {self.username}>"


# -----------------------------
# Project
# -----------------------------
class Project(Base,TenantMixin):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    description = Column(String)


    company = relationship("Company", back_populates="projects")

    created_at = Column(DateTime, default=utc_now)

    reports = relationship(
        "Report",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project {self.name}>"


# -----------------------------
# Report
# -----------------------------
class Report(Base,TenantMixin):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    project = relationship("Project", back_populates="reports")


    company = relationship("Company")

    content = Column(String)

    severity = Column(Integer)
    likelihood = Column(Integer)

    created_at = Column(DateTime, default=utc_now)

    usage_records = relationship(
        "Usage",
        back_populates="report",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Report {self.id}>"


# -----------------------------
# Usage Tracking
# -----------------------------
class Usage(Base):
    __tablename__ = "usage"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)

    month = Column(String, nullable=False)

    tokens = Column(Integer, default=0)
    reports = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="usage")
    report = relationship("Report", back_populates="usage_records")
    company = relationship("Company", back_populates="usage_records")

    def __repr__(self):
        return f"<Usage user={self.user_id} month={self.month}>"


# -----------------------------
# Inspection Checklist
# -----------------------------
class InspectionTemplate(Base):
    __tablename__ = "inspection_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String, nullable=True)
    json_schema = Column(JSON, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    questions = relationship(
        "InspectionQuestion",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="InspectionQuestion.order",
    )
    company = relationship("Company")
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<InspectionTemplate {self.name}>"


class InspectionQuestion(Base):
    __tablename__ = "inspection_questions"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("inspection_templates.id"), index=True, nullable=False)
    question = Column(String, nullable=False)
    question_code = Column(String, nullable=True)
    section_name = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)
    question_type = Column(String, nullable=True)
    order = Column(Integer, default=0)

    template = relationship("InspectionTemplate", back_populates="questions")
    responses = relationship(
        "InspectionResponse",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<InspectionQuestion {self.question[:40]}>"


class InspectionResponse(Base):
    __tablename__ = "inspection_responses"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("inspection_questions.id"), index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    answered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    answer = Column(String, nullable=False)      # "pass", "fail", "na"
    notes = Column(String)
    submitted_at = Column(DateTime, default=utc_now, index=True)

    question = relationship("InspectionQuestion", back_populates="responses")
    company = relationship("Company")
    answered_by = relationship("User", foreign_keys=[answered_by_id])

    def __repr__(self):
        return f"<InspectionResponse q={self.question_id} answer={self.answer}>"


# -----------------------------
# Hazard Tasks
# -----------------------------
class TaskStatusEnum(enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class TaskPriorityEnum(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class HazardTask(Base):
    __tablename__ = "hazard_tasks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)

    title = Column(String, nullable=False)
    description = Column(String)
    hazard_type = Column(String)                                  # e.g. "No helmet", "Loose ladder"
    priority = Column(Enum(TaskPriorityEnum), default=TaskPriorityEnum.medium, nullable=False)
    status = Column(Enum(TaskStatusEnum), default=TaskStatusEnum.open, nullable=False)

    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by_id  = Column(Integer, ForeignKey("users.id"), nullable=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    deadline     = Column(DateTime, nullable=True)
    resolved_at  = Column(DateTime, nullable=True)
    proof_notes  = Column(String, nullable=True)               # text proof when resolving

    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    created_by  = relationship("User", foreign_keys=[created_by_id])
    company = relationship("Company")
    project     = relationship("Project")

    def __repr__(self):
        return f"<HazardTask {self.id} {self.status}>"


# -----------------------------
# Incidents & Investigations
# -----------------------------
class IncidentSeverityEnum(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatusEnum(enum.Enum):
    open = "open"
    investigating = "investigating"
    closed = "closed"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    incident_type = Column(String, nullable=False)
    location = Column(String, nullable=True)
    description = Column(String, nullable=False)

    severity = Column(Enum(IncidentSeverityEnum), default=IncidentSeverityEnum.low, nullable=False)
    status = Column(Enum(IncidentStatusEnum), default=IncidentStatusEnum.open, nullable=False)

    immediate_action = Column(String, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    reporter = relationship("User", foreign_keys=[reported_by])
    company = relationship("Company")
    project = relationship("Project")
    investigation = relationship(
        "IncidentInvestigation",
        back_populates="incident",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self):
        return f"<Incident {self.id} {self.status}>"


class IncidentInvestigation(Base):
    __tablename__ = "incident_investigations"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False, unique=True, index=True)

    root_cause = Column(String, nullable=False)
    corrective_action = Column(String, nullable=False)
    contributing_factor = Column(String, nullable=True)
    investigated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    incident = relationship("Incident", back_populates="investigation")
    investigated_by = relationship("User", foreign_keys=[investigated_by_id])

    def __repr__(self):
        return f"<IncidentInvestigation incident={self.incident_id}>"


# -----------------------------
# Training & Certification
# -----------------------------
class TrainingCourse(Base):
    __tablename__ = "training_courses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    validity_months = Column(Integer, nullable=False, default=12)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    company = relationship("Company")
    records = relationship("TrainingRecord", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TrainingCourse {self.name}>"


class TrainingRecord(Base):
    __tablename__ = "training_records"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("training_courses.id"), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    completed_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    certificate_ref = Column(String, nullable=True)

    assigned_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    company = relationship("Company")
    user = relationship("User", foreign_keys=[user_id])
    course = relationship("TrainingCourse", back_populates="records")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])

    def __repr__(self):
        return f"<TrainingRecord user={self.user_id} course={self.course_id}>"


# -----------------------------
# Equipment & Asset Inspections
# -----------------------------
class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    status = Column(String, nullable=False, default="safe")
    inspection_interval_days = Column(Integer, nullable=False, default=30)
    last_inspection_date = Column(DateTime, nullable=True)
    next_inspection_date = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    company = relationship("Company")
    inspections = relationship(
        "EquipmentInspection",
        back_populates="equipment",
        cascade="all, delete-orphan",
        order_by="EquipmentInspection.inspection_date.desc()",
    )

    def __repr__(self):
        return f"<Equipment {self.name}>"


class EquipmentInspection(Base):
    __tablename__ = "equipment_inspections"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False, index=True)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String, nullable=False)
    inspection_date = Column(DateTime, default=utc_now, nullable=False, index=True)
    checklist_summary = Column(String, nullable=True)
    issues_found = Column(String, nullable=True)
    maintenance_task_id = Column(Integer, ForeignKey("hazard_tasks.id"), nullable=True)

    company = relationship("Company")
    equipment = relationship("Equipment", back_populates="inspections")
    inspector = relationship("User", foreign_keys=[inspector_id])
    maintenance_task = relationship("HazardTask", foreign_keys=[maintenance_task_id])

    def __repr__(self):
        return f"<EquipmentInspection equipment={self.equipment_id} status={self.status}>"


# -----------------------------
# Compliance & Regulation Tracking
# -----------------------------
class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    rule_name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    regulation_source = Column(String, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    company = relationship("Company")
    checks = relationship(
        "ComplianceCheck",
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="ComplianceCheck.checked_at.desc()",
    )

    def __repr__(self):
        return f"<ComplianceRule {self.rule_name}>"


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    rule_id = Column(Integer, ForeignKey("compliance_rules.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    checked_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, nullable=False)
    location = Column(String, nullable=True)
    evidence = Column(String, nullable=True)
    recommended_action = Column(String, nullable=True)
    maintenance_task_id = Column(Integer, ForeignKey("hazard_tasks.id"), nullable=True)
    checked_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    company = relationship("Company")
    rule = relationship("ComplianceRule", back_populates="checks")
    project = relationship("Project")
    checked_by = relationship("User", foreign_keys=[checked_by_id])
    maintenance_task = relationship("HazardTask", foreign_keys=[maintenance_task_id])

    def __repr__(self):
        return f"<ComplianceCheck rule={self.rule_id} status={self.status}>"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    action = Column(String, nullable=False)
    event_type = Column(String, nullable=False, default="user")
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)

    company = relationship("Company")
    user = relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.event_type} {self.action}>"


class IntegrationTypeEnum(enum.Enum):
    email = "email"
    slack = "slack"
    teams = "teams"
    webhook = "webhook"


class IntegrationEndpoint(Base):
    __tablename__ = "integration_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    integration_type = Column(Enum(IntegrationTypeEnum), nullable=False)
    name = Column(String, nullable=True)
    target = Column(String, nullable=False)
    secret = Column(String, nullable=True)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    company = relationship("Company")

    def __repr__(self):
        return f"<IntegrationEndpoint {self.integration_type} {self.target}>"


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=False)
    name = Column(String, nullable=False)
    key_prefix = Column(String, index=True, nullable=False)
    key_hash = Column(String, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    company = relationship("Company")

    def __repr__(self):
        return f"<ApiKey {self.name} company={self.company_id}>"


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    timezone = Column(String, nullable=False, default="UTC")
    notify_high_risk = Column(Integer, default=1, nullable=False)
    notify_weekly = Column(Integer, default=1, nullable=False)
    notify_maintenance = Column(Integer, default=0, nullable=False)
    notify_recommendations = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings user={self.user_id}>"


class UserAccountState(Base):
    __tablename__ = "user_account_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="account_state")

    def __repr__(self):
        return f"<UserAccountState user={self.user_id} active={self.is_active}>"
