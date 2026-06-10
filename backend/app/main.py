from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import Depends, HTTPException, Query, Response, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .auth import (
    authenticate_user,
    can_access_task,
    can_manage_issue,
    can_manage_test_case,
    can_view_all_tasks,
    create_access_token,
    create_user,
    get_current_user,
    require_roles,
)
from .config import Settings, get_settings
from .database import get_db, init_db
from .models import ReviewIssue, TestCase, User, UserRole
from .schemas import (
    AuditLogOut,
    AuthOut,
    HealthOut,
    IssueOut,
    IssueUpdate,
    LoginRequest,
    PromptTemplateCreate,
    PromptTemplateOut,
    PromptTemplateUpdate,
    ReviewRequest,
    TaskOut,
    TaskSummary,
    TestCaseOut,
    TestCaseUpdate,
    UserCreate,
    UserOut,
)
from .service import (
    create_prompt_template,
    create_review_task,
    get_task,
    list_audit_logs,
    list_prompt_templates,
    list_tasks,
    render_markdown_report,
    update_prompt_template,
    update_issue_status,
    update_test_status,
)
from .reporting import render_docx_report, render_pdf_report


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(
    title="CodeMate API",
    description="AI-assisted code review and test case generation API.",
    version="0.1.0",
    lifespan=lifespan,
)


settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthOut)
def health(settings_: Settings = Depends(get_settings)) -> HealthOut:
    return HealthOut(
        status="ok",
        demo_mode=settings_.codemate_demo_mode,
        openai_configured=bool(settings_.openai_api_key),
        auth_required=True,
    )


@app.post("/api/auth/login", response_model=AuthOut)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    settings_: Settings = Depends(get_settings),
) -> AuthOut:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return AuthOut(access_token=create_access_token(user, settings_), user=user)


@app.post("/api/auth/register", response_model=AuthOut)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    settings_: Settings = Depends(get_settings),
) -> AuthOut:
    if not settings_.allow_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    user = create_user(db, payload.username, payload.password, UserRole.developer.value)
    return AuthOut(access_token=create_access_token(user, settings_), user=user)


@app.get("/api/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return current_user


@app.post("/api/review-tasks", response_model=TaskOut)
def create_task(
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    settings_: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    return create_review_task(db, settings_, payload, current_user)


@app.get("/api/review-tasks", response_model=list[TaskSummary])
def tasks(
    include_all: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskSummary]:
    show_all = include_all and can_view_all_tasks(current_user)
    return list_tasks(db, current_user, include_all=show_all)


@app.get("/api/review-tasks/{task_id}", response_model=TaskOut)
def task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    found = get_task(db, task_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not can_access_task(current_user, found.user_id):
        raise HTTPException(status_code=403, detail="Task access denied")
    return found


@app.patch("/api/issues/{issue_id}", response_model=IssueOut)
def update_issue(
    issue_id: int,
    payload: IssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IssueOut:
    existing = db.get(ReviewIssue, issue_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not can_manage_issue(current_user, existing.task.user_id):
        raise HTTPException(status_code=403, detail="Issue access denied")
    issue = update_issue_status(
        db, issue_id, payload.status, payload.reviewer_note, current_user
    )
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@app.patch("/api/test-cases/{test_id}", response_model=TestCaseOut)
def update_test_case(
    test_id: int,
    payload: TestCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestCaseOut:
    existing = db.get(TestCase, test_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    if not can_manage_test_case(current_user, existing.task.user_id):
        raise HTTPException(status_code=403, detail="Test case access denied")
    test_case = update_test_status(db, test_id, payload.status, current_user)
    if test_case is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    return test_case


@app.get("/api/review-tasks/{task_id}/report.md")
def report(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    found = get_task(db, task_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not can_access_task(current_user, found.user_id):
        raise HTTPException(status_code=403, detail="Task access denied")
    markdown = render_markdown_report(found)
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="codemate-task-{task_id}.md"'
        },
    )


@app.get("/api/review-tasks/{task_id}/report.pdf")
def report_pdf(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    found = get_task(db, task_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not can_access_task(current_user, found.user_id):
        raise HTTPException(status_code=403, detail="Task access denied")
    content = render_pdf_report(found)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="codemate-task-{task_id}.pdf"'
        },
    )


@app.get("/api/review-tasks/{task_id}/report.docx")
def report_docx(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    found = get_task(db, task_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not can_access_task(current_user, found.user_id):
        raise HTTPException(status_code=403, detail="Task access denied")
    content = render_docx_report(found)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="codemate-task-{task_id}.docx"'
        },
    )


@app.get("/api/admin/users", response_model=list[UserOut])
def admin_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin.value)),
) -> list[UserOut]:
    return list(db.query(User).order_by(User.created_at.desc()).all())


@app.post("/api/admin/users", response_model=UserOut)
def admin_create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin.value)),
) -> UserOut:
    return create_user(db, payload.username, payload.password, payload.role)


@app.get("/api/admin/prompt-templates", response_model=list[PromptTemplateOut])
def admin_prompt_templates(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin.value)),
) -> list[PromptTemplateOut]:
    return list_prompt_templates(db)


@app.post("/api/admin/prompt-templates", response_model=PromptTemplateOut)
def admin_create_prompt_template(
    payload: PromptTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin.value)),
) -> PromptTemplateOut:
    try:
        return create_prompt_template(db, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.patch("/api/admin/prompt-templates/{template_id}", response_model=PromptTemplateOut)
def admin_update_prompt_template(
    template_id: int,
    payload: PromptTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin.value)),
) -> PromptTemplateOut:
    template = update_prompt_template(db, template_id, payload, current_user)
    if template is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return template


@app.get("/api/admin/audit-logs", response_model=list[AuditLogOut])
def admin_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin.value)),
) -> list[AuditLogOut]:
    return list_audit_logs(db, limit=limit)


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")


@app.get("/")
def serve_frontend() -> FileResponse:
    index = frontend_dist / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend has not been built")
    return FileResponse(index)


@app.get("/{path:path}")
def serve_spa(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    index = frontend_dist / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend has not been built")
    return FileResponse(index)
