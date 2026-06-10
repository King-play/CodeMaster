from __future__ import annotations

import json
import re
from textwrap import dedent

from openai import OpenAI
from pydantic import ValidationError

from .config import Settings
from .schemas import IssueCreate, ReviewResult, TestCaseCreate


REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "issues", "test_cases"],
    "properties": {
        "summary": {"type": "string"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "type",
                    "severity",
                    "file",
                    "line_start",
                    "line_end",
                    "description",
                    "suggestion",
                    "confidence",
                    "source",
                ],
                "properties": {
                    "type": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "info"],
                    },
                    "file": {"type": "string"},
                    "line_start": {"type": "integer", "minimum": 1},
                    "line_end": {"type": "integer", "minimum": 1},
                    "description": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                },
            },
        },
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "category", "input", "expected", "priority"],
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "input": {"type": "string"},
                    "expected": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
    },
}


SYSTEM_PROMPT = dedent(
    """
    You are CodeMate, an AI assistant for code review and test case design.
    Focus on actionable defects, boundary conditions, exception handling,
    maintainability, and security. Every issue must cite a file and line range.
    Do not invent facts that are not supported by the submitted code or static
    findings. Mark uncertainty with confidence. Return concise Chinese text.
    """
).strip()


def build_review_prompt(
    *,
    project_name: str,
    file_name: str,
    language: str,
    source_kind: str,
    code: str,
    static_issues: list[IssueCreate],
    review_standard: str = "",
) -> str:
    static_payload = [issue.model_dump() for issue in static_issues]
    return dedent(
        f"""
        Project: {project_name}
        File: {file_name}
        Language: {language}
        Source kind: {source_kind}

        Static analysis findings:
        {json.dumps(static_payload, ensure_ascii=False, indent=2)}

        Team review standard:
        {review_standard or "Use the default CodeMate review standard."}

        Review goals:
        1. Find likely bugs, missing boundary checks, exception handling gaps, maintainability issues, and security risks.
        2. Generate normal-path, boundary, exceptional, and security-related test cases when relevant.
        3. Prefer a small set of high-signal findings over noisy style comments.
        4. Output only data that matches the required JSON schema.

        Code:
        ```{language}
        {code}
        ```
        """
    ).strip()


def review_with_ai(
    settings: Settings,
    *,
    project_name: str,
    file_name: str,
    language: str,
    source_kind: str,
    code: str,
    static_issues: list[IssueCreate],
    review_standard: str = "",
) -> ReviewResult:
    if settings.codemate_demo_mode or not settings.openai_api_key:
        return demo_review(
            project_name=project_name,
            file_name=file_name,
            language=language,
            code=code,
            static_issues=static_issues,
            review_standard=review_standard,
        )

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        instructions=SYSTEM_PROMPT,
        input=build_review_prompt(
            project_name=project_name,
            file_name=file_name,
            language=language,
            source_kind=source_kind,
            code=code,
            static_issues=static_issues,
            review_standard=review_standard,
        ),
        text={
            "format": {
                "type": "json_schema",
                "name": "codemate_review",
                "strict": True,
                "schema": REVIEW_SCHEMA,
            }
        },
    )
    raw = response.output_text
    try:
        return ReviewResult.model_validate_json(raw)
    except ValidationError:
        return ReviewResult.model_validate(json.loads(raw))


def demo_review(
    *,
    project_name: str,
    file_name: str,
    language: str,
    code: str,
    static_issues: list[IssueCreate],
    review_standard: str = "",
) -> ReviewResult:
    issues = list(static_issues)
    test_cases: list[TestCaseCreate] = []
    lines = code.splitlines()

    if _contains_input_without_validation(code):
        line = _first_matching_line(lines, r"input\(|request\.|req\.|params|body")
        issues.append(
            IssueCreate(
                type="input_validation_missing",
                severity="medium",
                file=file_name,
                line_start=line,
                line_end=line,
                description="输入数据在进入业务逻辑前缺少明确校验，可能导致边界值或非法格式进入后续流程。",
                suggestion="在入口处增加类型、长度、范围和必填字段校验，并为失败路径返回清晰错误。",
                confidence=0.74,
                source="ai-demo",
            )
        )
        test_cases.append(
            TestCaseCreate(
                name="非法输入应被拒绝",
                category="exception",
                input="提交空值、超长字符串或错误类型字段",
                expected="系统返回校验错误，不继续执行核心业务逻辑",
                priority="high",
            )
        )

    if _contains_numeric_comparison(code):
        line = _first_matching_line(lines, r"[<>]=?|==")
        test_cases.extend(
            [
                TestCaseCreate(
                    name="边界值等于阈值",
                    category="boundary",
                    input="传入刚好等于判断阈值的数据",
                    expected="结果与业务规则定义一致，且不会走错分支",
                    priority="high",
                ),
                TestCaseCreate(
                    name="边界值低于阈值",
                    category="boundary",
                    input="传入刚好低于阈值的数据",
                    expected="系统进入预期的异常或低值分支",
                    priority="medium",
                ),
            ]
        )
        if not any(issue.type == "boundary_condition_missing" for issue in issues):
            issues.append(
                IssueCreate(
                    type="boundary_condition_missing",
                    severity="medium",
                    file=file_name,
                    line_start=line,
                    line_end=line,
                    description="代码包含条件判断，但缺少能证明边界行为的测试建议或显式注释。",
                    suggestion="补充等于阈值、低于阈值、高于阈值三类测试，并确认业务规则。",
                    confidence=0.66,
                    source="ai-demo",
                )
            )

    if "except:" in code or "catch (" in code and "console.log" in code:
        line = _first_matching_line(lines, r"except:|catch")
        issues.append(
            IssueCreate(
                type="broad_exception_handling",
                severity="medium",
                file=file_name,
                line_start=line,
                line_end=line,
                description="异常处理过宽或只记录日志，可能掩盖真实失败原因。",
                suggestion="捕获具体异常类型，保留上下文，并让调用方能够感知失败。",
                confidence=0.72,
                source="ai-demo",
            )
        )

    if not test_cases:
        test_cases.append(
            TestCaseCreate(
                name="正常路径执行成功",
                category="normal",
                input="提供一组满足前置条件的有效输入",
                expected="函数返回预期结果，且没有产生未处理异常",
                priority="medium",
            )
        )

    if not issues:
        issues.append(
            IssueCreate(
                type="manual_review_recommended",
                severity="info",
                file=file_name,
                line_start=1,
                line_end=max(1, min(len(lines), 1)),
                description="本地演示审查未发现明显高风险问题，仍建议由人工确认关键业务逻辑。",
                suggestion="重点检查需求约束、权限边界和测试覆盖是否满足项目标准。",
                confidence=0.55,
                source="ai-demo",
            )
        )

    summary = (
        f"{project_name} 的演示审查完成：发现 {len(issues)} 条建议，"
        f"生成 {len(test_cases)} 个测试场景。配置 OPENAI_API_KEY 并关闭 demo mode 后可启用真实模型审查。"
    )
    if review_standard:
        summary += " 当前已应用管理员配置的审查标准。"
    return ReviewResult(summary=summary, issues=issues[:10], test_cases=test_cases[:10])


def _contains_input_without_validation(code: str) -> bool:
    has_input = bool(re.search(r"input\(|request\.|req\.|params|body", code))
    has_validation = bool(re.search(r"validate|schema|required|isdigit|isinstance|pydantic", code, re.I))
    return has_input and not has_validation


def _contains_numeric_comparison(code: str) -> bool:
    return bool(re.search(r"\b(if|while|return)\b[^\n]*(<=|>=|<|>|==)", code))


def _first_matching_line(lines: list[str], pattern: str) -> int:
    regex = re.compile(pattern)
    for index, line in enumerate(lines, start=1):
        if regex.search(line):
            return index
    return 1
