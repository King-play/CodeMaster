"""initial schema

Revision ID: 20260610_0001
Revises:
Create Date: 2026-06-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260610_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"])
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Integer(), nullable=False),
    )
    op.create_index(op.f("ix_prompt_templates_id"), "prompt_templates", ["id"])
    op.create_index(op.f("ix_prompt_templates_name"), "prompt_templates", ["name"], unique=True)

    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("project_name", sa.String(length=160), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(op.f("ix_review_tasks_id"), "review_tasks", ["id"])

    op.create_table(
        "code_inputs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("review_tasks.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("code_excerpt", sa.Text(), nullable=False),
        sa.Column("diff_text", sa.Text(), nullable=False),
        sa.Column("redaction_count", sa.Integer(), nullable=False),
    )
    op.create_index(op.f("ix_code_inputs_id"), "code_inputs", ["id"])
    op.create_index(op.f("ix_code_inputs_task_id"), "code_inputs", ["task_id"])
    op.create_index(op.f("ix_code_inputs_code_hash"), "code_inputs", ["code_hash"])

    op.create_table(
        "review_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("review_tasks.id"), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("file", sa.String(length=255), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=False),
        sa.Column("line_end", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(op.f("ix_review_issues_id"), "review_issues", ["id"])
    op.create_index(op.f("ix_review_issues_task_id"), "review_issues", ["task_id"])

    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("review_tasks.id"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("expected", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
    )
    op.create_index(op.f("ix_test_cases_id"), "test_cases", ["id"])
    op.create_index(op.f("ix_test_cases_task_id"), "test_cases", ["task_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("review_tasks.id"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("test_cases")
    op.drop_table("review_issues")
    op.drop_table("code_inputs")
    op.drop_table("review_tasks")
    op.drop_table("prompt_templates")
    op.drop_table("users")

