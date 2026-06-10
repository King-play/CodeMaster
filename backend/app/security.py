from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    count: int
    findings: list[str]


SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+")),
    (
        "AWS access key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "Private key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
    (
        "Database URL",
        re.compile(r"\b(?:postgres|mysql|mongodb)://[^\s'\"<>]+", re.IGNORECASE),
    ),
    (
        "Password assignment",
        re.compile(
            r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\s*=\s*['\"][^'\"]{6,}['\"]"
        ),
    ),
]


def redact_secrets(text: str) -> RedactionResult:
    redacted = text
    count = 0
    findings: list[str] = []

    for label, pattern in SECRET_PATTERNS:
        matches = list(pattern.finditer(redacted))
        if matches:
            findings.append(label)
            count += len(matches)
            redacted = pattern.sub(f"[REDACTED {label.upper()}]", redacted)

    return RedactionResult(text=redacted, count=count, findings=findings)


def clamp_code(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[TRUNCATED: input exceeded configured limit]", True

