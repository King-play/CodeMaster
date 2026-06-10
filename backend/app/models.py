from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserRole(str, Enum):
    developer = "developer"
    reviewer = "reviewer"
    tester = "tester"
    admin = "admin"


class TaskStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class IssueStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    ignored = "ignored"
    fixed = "fixed"


class TestStatus(str, Enum):
    suggested = "suggested"
    implemented = "implemented"
    skipped = "skipped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=UserRole.developer.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tasks: Mapped[list["ReviewTask"]] = relationship(back_populates="user")


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    project_name: Mapped[str] = mapped_column(String(160), default="Untitled project")
    language: Mapped[str] = mapped_column(String(40), default="unknown")
    status: Mapped[str] = mapped_column(String(24), default=TaskStatus.pending.value)
    summary: Mapped[str] = mapped_column(Text, default="")
    source_kind: Mapped[str] = mapped_column(String(24), default="snippet")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped[Optional[User]] = relationship(back_populates="tasks")
    input: Mapped["CodeInput"] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )
    issues: Mapped[list["ReviewIssue"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class CodeInput(Base):
    __tablename__ = "code_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("review_tasks.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(255), default="snippet.txt")
    code_hash: Mapped[str] = mapped_column(String(128), index=True)
    code_excerpt: Mapped[str] = mapped_column(Text, default="")
    diff_text: Mapped[str] = mapped_column(Text, default="")
    redaction_count: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped[ReviewTask] = relationship(back_populates="input")


class ReviewIssue(Base):
    __tablename__ = "review_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("review_tasks.id"), index=True)
    type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(24))
    file: Mapped[str] = mapped_column(String(255), default="snippet")
    line_start: Mapped[int] = mapped_column(Integer, default=1)
    line_end: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(24), default=IssueStatus.pending.value)
    source: Mapped[str] = mapped_column(String(24), default="static")
    reviewer_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped[ReviewTask] = relationship(back_populates="issues")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("review_tasks.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(40))
    input: Mapped[str] = mapped_column(Text)
    expected: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(24), default="medium")
    status: Mapped[str] = mapped_column(String(24), default=TestStatus.suggested.value)

    task: Mapped[ReviewTask] = relationship(back_populates="test_cases")


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    template: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(40), default="1.0.0")
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("review_tasks.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(80), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped[Optional[ReviewTask]] = relationship(back_populates="audit_logs")
