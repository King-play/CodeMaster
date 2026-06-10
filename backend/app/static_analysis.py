from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .schemas import IssueCreate


@dataclass(frozen=True)
class StaticFinding:
    issue: IssueCreate


TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK)\b", re.IGNORECASE)
SQL_CONCAT_PATTERN = re.compile(
    r"(SELECT|UPDATE|DELETE|INSERT)\s+.+(\+|f['\"]|%|\{)", re.IGNORECASE
)
DANGEROUS_CALLS = {
    "eval": "Avoid eval because user-controlled input can execute arbitrary code.",
    "exec": "Avoid exec because user-controlled input can execute arbitrary code.",
}


def analyze_code(
    code: str, language: str, file_name: str, settings: Settings | None = None
) -> list[IssueCreate]:
    issues: list[IssueCreate] = []
    issues.extend(_generic_checks(code, file_name))

    if language == "python":
        issues.extend(_python_checks(code, file_name))
        if settings is None or settings.codemate_enable_external_analyzers:
            issues.extend(_pylint_checks(code, file_name))
    elif language in {"javascript", "typescript"}:
        issues.extend(_js_checks(code, file_name))
        if settings is None or settings.codemate_enable_external_analyzers:
            issues.extend(_eslint_checks(code, language, file_name))

    return _dedupe(issues)


def _generic_checks(code: str, file_name: str) -> list[IssueCreate]:
    issues: list[IssueCreate] = []
    lines = code.splitlines()
    for index, line in enumerate(lines, start=1):
        if TODO_PATTERN.search(line):
            issues.append(
                IssueCreate(
                    type="unfinished_work",
                    severity="low",
                    file=file_name,
                    line_start=index,
                    line_end=index,
                    description="The code contains TODO/FIXME/HACK markers that should be resolved or tracked before release.",
                    suggestion="Convert the marker into a tracked issue or complete the implementation before merging.",
                    confidence=0.78,
                    source="static",
                )
            )
        if len(line) > 140:
            issues.append(
                IssueCreate(
                    type="maintainability_line_length",
                    severity="info",
                    file=file_name,
                    line_start=index,
                    line_end=index,
                    description="This line is unusually long and may be difficult to review.",
                    suggestion="Break the expression into named variables or multiple lines.",
                    confidence=0.68,
                    source="static",
                )
            )
        if SQL_CONCAT_PATTERN.search(line):
            issues.append(
                IssueCreate(
                    type="sql_injection_risk",
                    severity="high",
                    file=file_name,
                    line_start=index,
                    line_end=index,
                    description="A SQL statement appears to be built through string interpolation or concatenation.",
                    suggestion="Use parameterized queries or the framework's query builder instead of assembling SQL strings.",
                    confidence=0.82,
                    source="static",
                )
            )
    return issues


def _python_checks(code: str, file_name: str) -> list[IssueCreate]:
    issues: list[IssueCreate] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [
            IssueCreate(
                type="syntax_error",
                severity="critical",
                file=file_name,
                line_start=exc.lineno or 1,
                line_end=exc.lineno or 1,
                description=f"Python syntax error: {exc.msg}.",
                suggestion="Fix the syntax error before running AI-assisted semantic review.",
                confidence=0.97,
                source="static",
            )
        ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name in DANGEROUS_CALLS:
                issues.append(
                    IssueCreate(
                        type="dangerous_dynamic_execution",
                        severity="high",
                        file=file_name,
                        line_start=getattr(node, "lineno", 1),
                        line_end=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                        description=DANGEROUS_CALLS[name],
                        suggestion="Replace dynamic execution with explicit parsing, validation, or a safe dispatch table.",
                        confidence=0.9,
                        source="static",
                    )
                )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _function_complexity(node) >= 8:
                issues.append(
                    IssueCreate(
                        type="high_branch_complexity",
                        severity="medium",
                        file=file_name,
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno),
                        description=f"Function `{node.name}` has many branches, which increases review and testing risk.",
                        suggestion="Split the function into smaller units and add branch-focused tests.",
                        confidence=0.76,
                        source="static",
                    )
                )
    return issues


def _pylint_checks(code: str, file_name: str) -> list[IssueCreate]:
    if shutil.which("python") is None:
        return []
    suffix = Path(file_name).suffix or ".py"
    try:
        with tempfile.TemporaryDirectory(prefix="codemate-pylint-") as tmp:
            target = Path(tmp) / f"snippet{suffix}"
            target.write_text(code, encoding="utf-8")
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "pylint",
                    "--output-format=json",
                    "--score=n",
                    str(target),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=12,
                check=False,
            )
        if not result.stdout.strip():
            return []
        messages = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []

    issues: list[IssueCreate] = []
    for message in messages[:30]:
        issues.append(
            IssueCreate(
                type=f"pylint_{message.get('symbol', 'message')}",
                severity=_pylint_severity(message.get("type", "")),
                file=file_name,
                line_start=max(1, int(message.get("line") or 1)),
                line_end=max(1, int(message.get("line") or 1)),
                description=message.get("message", "Pylint reported an issue."),
                suggestion="Review the Pylint finding and adjust the implementation or project lint configuration.",
                confidence=0.84,
                source="pylint",
            )
        )
    return issues


def _js_checks(code: str, file_name: str) -> list[IssueCreate]:
    issues: list[IssueCreate] = []
    for index, line in enumerate(code.splitlines(), start=1):
        if "eval(" in line or "new Function(" in line:
            issues.append(
                IssueCreate(
                    type="dangerous_dynamic_execution",
                    severity="high",
                    file=file_name,
                    line_start=index,
                    line_end=index,
                    description="Dynamic code execution can turn user-controlled data into executable code.",
                    suggestion="Use structured parsing or a whitelisted dispatch table instead.",
                    confidence=0.88,
                    source="static",
                )
            )
        if re.search(r"\bvar\b", line):
            issues.append(
                IssueCreate(
                    type="modernization_var_usage",
                    severity="info",
                    file=file_name,
                    line_start=index,
                    line_end=index,
                    description="The code uses `var`, which has function scope and can hide subtle bugs.",
                    suggestion="Prefer `const` or `let` according to whether the binding is reassigned.",
                    confidence=0.7,
                    source="static",
                )
            )
    return issues


def _eslint_checks(code: str, language: str, file_name: str) -> list[IssueCreate]:
    npx = shutil.which("npx")
    if npx is None:
        return []
    suffix = ".ts" if language == "typescript" else ".js"
    if Path(file_name).suffix in {".js", ".jsx", ".ts", ".tsx"}:
        suffix = Path(file_name).suffix
    try:
        with tempfile.TemporaryDirectory(prefix="codemate-eslint-") as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / f"snippet{suffix}"
            config = tmp_path / "eslint.config.js"
            target.write_text(code, encoding="utf-8")
            config.write_text(
                """
export default [
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    languageOptions: { ecmaVersion: "latest", sourceType: "module" },
    rules: {
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-var": "warn",
      "eqeqeq": "warn",
      "no-unused-vars": "warn"
    }
  }
];
""".strip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    npx,
                    "eslint",
                    "--no-config-lookup",
                    "--config",
                    str(config),
                    "--format",
                    "json",
                    str(target),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
                check=False,
            )
        if not result.stdout.strip():
            return []
        payload = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []

    issues: list[IssueCreate] = []
    for file_result in payload:
        for message in file_result.get("messages", [])[:30]:
            issues.append(
                IssueCreate(
                    type=f"eslint_{message.get('ruleId') or 'parser'}",
                    severity="high" if message.get("severity") == 2 else "medium",
                    file=file_name,
                    line_start=max(1, int(message.get("line") or 1)),
                    line_end=max(1, int(message.get("endLine") or message.get("line") or 1)),
                    description=message.get("message", "ESLint reported an issue."),
                    suggestion="Review the ESLint finding and adjust the implementation or lint configuration.",
                    confidence=0.82,
                    source="eslint",
                )
            )
    return issues


def _call_name(func: ast.expr) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _function_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    branch_types = [ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BoolOp]
    if hasattr(ast, "Match"):
        branch_types.append(ast.Match)
    branches = tuple(branch_types)
    return sum(isinstance(child, branches) for child in ast.walk(node))


def _pylint_severity(message_type: str) -> str:
    return {
        "fatal": "critical",
        "error": "high",
        "warning": "medium",
        "refactor": "low",
        "convention": "info",
        "information": "info",
    }.get(message_type, "info")


def _dedupe(issues: list[IssueCreate]) -> list[IssueCreate]:
    seen: set[tuple[str, str, int, str]] = set()
    unique: list[IssueCreate] = []
    for issue in issues:
        key = (issue.type, issue.file, issue.line_start, issue.source)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique[:40]
