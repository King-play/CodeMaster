from pathlib import Path


EXTENSION_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".sql": "sql",
}


def detect_language(file_name: str, code: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix in EXTENSION_LANGUAGE:
        return EXTENSION_LANGUAGE[suffix]

    stripped = code.lstrip()
    if stripped.startswith("diff --git") or "\n+++" in code[:1000]:
        return "diff"
    if "def " in code and ":" in code:
        return "python"
    if "function " in code or "const " in code or "=>" in code:
        return "javascript"
    if "public class " in code or "private " in code:
        return "java"
    return "unknown"

