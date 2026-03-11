from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum


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

    users = relationship("User", back_populates="company", cascade="all, delete")
    projects = relationship("Project", back_populates="company", cascade="all, delete")
    usage_records = relationship("Usage", back_populates="company", cascade="all, delete")


# -----------------------------
# User
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(Enum(RoleEnum), default=RoleEnum.worker, nullable=False)

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="users")

    usage = relationship("Usage", back_populates="user")


# -----------------------------
# Project
# -----------------------------
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="projects")

    created_at = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="project", cascade="all, delete")


# -----------------------------
# Report
# -----------------------------
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("Project", back_populates="reports")

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company")

    content = Column(String)

    severity = Column(Integer)
    likelihood = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    usage_records = relationship("Usage", back_populates="report")


# -----------------------------
# Usage Tracking
# -----------------------------
class Usage(Base):
    __tablename__ = "usage"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("reports.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))

    month = Column(String, nullable=False)

    tokens = Column(Integer, default=0)
    reports = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="usage")
    report = relationship("Report", back_populates="usage_records")
    company = relationship("Company", back_populates="usage_records")