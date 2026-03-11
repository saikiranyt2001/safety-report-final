from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum

class RoleEnum(enum.Enum):
    admin = "admin"
    manager = "manager"
    worker = "worker"

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", back_populates="company", cascade="all, delete")
    projects = relationship("Project", back_populates="company", cascade="all, delete")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(Enum(RoleEnum), default=RoleEnum.worker, nullable=False)

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="users")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="projects")

    created_at = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="project", cascade="all, delete")

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

class Usage(Base):
    __tablename__ = "usage"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("reports.id"))

    company_id = Column(Integer, ForeignKey("companies.id"))

    month = Column(String, nullable=False)

    tokens = Column(Integer, default=0)
    reports = Column(Integer, default=0)
    cost = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    report = relationship("Report")
