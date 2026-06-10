from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .ai_client import review_with_ai
from .config import Settings
from .language import detect_language
from .models import (
    AuditLog,
    CodeInput,
    PromptTemplate,
    ReviewIssue,
    ReviewTask,
    TestCase,
    TaskStatus,
    User,
)
from .schemas import (
    IssueCreate,
    PromptTemplateCreate,
    PromptTemplateUpdate,
    ReviewRequest,
    ReviewResult,
)
from .reporting import render_markdown_report
from .security import clamp_code, redact_secrets
from .static_analysis import analyze_code


def create_review_task(
    db: Session, settings: Settings, payload: ReviewRequest, user: User
) -> ReviewTask:
    clamped_code, truncated = clamp_code(payload.code, settings.max_code_chars)
    redaction = redact_secrets(clamped_code)
    safe_code = redaction.text
    language = payload.language or detect_language(payload.file_name, safe_code)
    code_hash = hashlib.sha256(safe_code.encode("utf-8")).hexdigest()
    static_issues = analyze_code(safe_code, language, payload.file_name, settings)

    task = ReviewTask(
        user_id=user.id,
        project_name=payload.project_name,
        language=language,
        source_kind=payload.source_kind,
        status=TaskStatus.pending.value,
    )
    task.input = CodeInput(
        file_name=payload.file_name,
        code_hash=code_hash,
        code_excerpt=_excerpt(safe_code),
        diff_text=safe_code if payload.source_kind == "diff" else "",
        redaction_count=redaction.count,
    )
    db.add(task)
    db.flush()
    _audit(
        db,
        task=task,
        user_id=user.id,
        action="task.created",
        detail=f"Created task with {redaction.count} redactions"
        + (" and truncated input" if truncated else ""),
    )

    try:
        result = review_with_ai(
            settings,
            project_name=payload.project_name,
            file_name=payload.file_name,
            language=language,
            source_kind=payload.source_kind,
            code=safe_code,
            static_issues=static_issues,
            review_standard=get_enabled_review_standard(db),
        )
        _persist_result(db, task, result)
        task.status = TaskStatus.completed.value
        task.completed_at = datetime.utcnow()
        _audit(db, task=task, user_id=user.id, action="task.completed", detail=result.summary)
    except Exception as exc:
        task.status = TaskStatus.failed.value
        task.summary = f"Review failed: {exc}"
        _audit(db, task=task, user_id=user.id, action="task.failed", detail=str(exc))

    db.commit()
    db.refresh(task)
    return get_task(db, task.id) or task


def list_tasks(db: Session, user: User, include_all: bool = False) -> list[ReviewTask]:
    stmt = (
        select(ReviewTask)
        .options(selectinload(ReviewTask.input))
        .order_by(ReviewTask.created_at.desc())
    )
    if not include_all:
        stmt = stmt.where(ReviewTask.user_id == user.id)
    return list(db.scalars(stmt))


def get_task(db: Session, task_id: int) -> ReviewTask | None:
    stmt = (
        select(ReviewTask)
        .where(ReviewTask.id == task_id)
        .options(
            selectinload(ReviewTask.input),
            selectinload(ReviewTask.issues),
            selectinload(ReviewTask.test_cases),
        )
    )
    return db.scalar(stmt)


def update_issue_status(
    db: Session, issue_id: int, status: str, reviewer_note: str, user: User
) -> ReviewIssue | None:
    issue = db.get(ReviewIssue, issue_id)
    if issue is None:
        return None
    issue.status = status
    issue.reviewer_note = reviewer_note
    _audit(
        db,
        user_id=user.id,
        task_id=issue.task_id,
        action="issue.updated",
        target_id=str(issue_id),
        detail=f"status={status}",
    )
    db.commit()
    db.refresh(issue)
    return issue


def update_test_status(db: Session, test_id: int, status: str, user: User) -> TestCase | None:
    test_case = db.get(TestCase, test_id)
    if test_case is None:
        return None
    test_case.status = status
    _audit(
        db,
        user_id=user.id,
        task_id=test_case.task_id,
        action="test_case.updated",
        target_id=str(test_id),
        detail=f"status={status}",
    )
    db.commit()
    db.refresh(test_case)
    return test_case


def list_prompt_templates(db: Session) -> list[PromptTemplate]:
    stmt = select(PromptTemplate).order_by(PromptTemplate.enabled.desc(), PromptTemplate.name)
    return list(db.scalars(stmt))


def create_prompt_template(
    db: Session, payload: PromptTemplateCreate, user: User
) -> PromptTemplate:
    template = PromptTemplate(
        name=payload.name,
        template=payload.template,
        version=payload.version,
        enabled=1 if payload.enabled else 0,
    )
    try:
        db.add(template)
        db.flush()
        _audit(
            db,
            user_id=user.id,
            action="prompt_template.created",
            target_id=str(template.id),
            detail=template.name,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Prompt template name already exists") from exc
    db.refresh(template)
    return template


def update_prompt_template(
    db: Session, template_id: int, payload: PromptTemplateUpdate, user: User
) -> PromptTemplate | None:
    template = db.get(PromptTemplate, template_id)
    if template is None:
        return None
    if payload.template is not None:
        template.template = payload.template
    if payload.version is not None:
        template.version = payload.version
    if payload.enabled is not None:
        template.enabled = 1 if payload.enabled else 0
    _audit(
        db,
        user_id=user.id,
        action="prompt_template.updated",
        target_id=str(template.id),
        detail=template.name,
    )
    db.commit()
    db.refresh(template)
    return template


def list_audit_logs(db: Session, limit: int = 100) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def _persist_result(db: Session, task: ReviewTask, result: ReviewResult) -> None:
    task.summary = result.summary
    task.issues.clear()
    task.test_cases.clear()
    for issue in result.issues:
        task.issues.append(ReviewIssue(**issue.model_dump()))
    for test_case in result.test_cases:
        task.test_cases.append(TestCase(**test_case.model_dump()))
    db.flush()


def _excerpt(code: str, max_chars: int = 12000) -> str:
    if len(code) <= max_chars:
        return code
    return code[:max_chars] + "\n\n[EXCERPT TRUNCATED]"


def get_enabled_review_standard(db: Session) -> str:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.enabled == 1)
        .order_by(PromptTemplate.id.desc())
        .limit(1)
    )
    template = db.scalar(stmt)
    return template.template if template else ""


def _audit(
    db: Session,
    *,
    action: str,
    detail: str,
    user_id: int | None = None,
    task: ReviewTask | None = None,
    task_id: int | None = None,
    target_id: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            task=task,
            task_id=task_id,
            action=action,
            target_id=target_id,
            detail=detail[:2000],
        )
    )
