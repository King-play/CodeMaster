from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["critical", "high", "medium", "low", "info"]
IssueState = Literal["pending", "accepted", "ignored", "fixed"]
TestState = Literal["suggested", "implemented", "skipped"]
Role = Literal["developer", "reviewer", "tester", "admin"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Role = "developer"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    created_at: datetime


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class IssueCreate(BaseModel):
    type: str
    severity: Severity
    file: str = "snippet"
    line_start: int = Field(default=1, ge=1)
    line_end: int = Field(default=1, ge=1)
    description: str
    suggestion: str
    confidence: float = Field(default=0.5, ge=0, le=1)
    source: str = "ai"


class TestCaseCreate(BaseModel):
    name: str
    category: str
    input: str
    expected: str
    priority: Literal["high", "medium", "low"] = "medium"


class ReviewResult(BaseModel):
    summary: str
    issues: list[IssueCreate]
    test_cases: list[TestCaseCreate]


class ReviewRequest(BaseModel):
    project_name: str = Field(default="Untitled project", max_length=160)
    file_name: str = Field(default="snippet.txt", max_length=255)
    language: Optional[str] = Field(default=None, max_length=40)
    source_kind: Literal["snippet", "diff", "file"] = "snippet"
    code: str = Field(min_length=1)


class IssueUpdate(BaseModel):
    status: IssueState
    reviewer_note: str = ""


class TestCaseUpdate(BaseModel):
    status: TestState


class PromptTemplateCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    template: str = Field(min_length=20)
    version: str = Field(default="1.0.0", max_length=40)
    enabled: bool = True


class PromptTemplateUpdate(BaseModel):
    template: Optional[str] = Field(default=None, min_length=20)
    version: Optional[str] = Field(default=None, max_length=40)
    enabled: Optional[bool] = None


class PromptTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    template: str
    version: str
    enabled: bool


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    task_id: Optional[int]
    action: str
    target_id: str
    detail: str
    created_at: datetime


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    severity: str
    file: str
    line_start: int
    line_end: int
    description: str
    suggestion: str
    confidence: float
    status: str
    source: str
    reviewer_note: str


class TestCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    input: str
    expected: str
    priority: str
    status: str


class CodeInputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_name: str
    code_hash: str
    code_excerpt: str
    diff_text: str
    redaction_count: int


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    project_name: str
    language: str
    status: str
    summary: str
    source_kind: str
    created_at: datetime
    completed_at: Optional[datetime]
    input: Optional[CodeInputOut]
    issues: list[IssueOut] = []
    test_cases: list[TestCaseOut] = []


class TaskSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    project_name: str
    language: str
    status: str
    summary: str
    source_kind: str
    created_at: datetime
    completed_at: Optional[datetime]


class HealthOut(BaseModel):
    status: str
    demo_mode: bool
    openai_configured: bool
    auth_required: bool = True
