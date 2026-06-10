# Architecture

CodeMate has two runtime components:

- `backend`: FastAPI service with SQLite persistence, static analysis, sensitive-data redaction, OpenAI integration, and report export.
- `frontend`: React + TypeScript web app for task submission, review triage, test case tracking, and history browsing.

## Request Flow

1. User submits code, a file excerpt, or a Git diff.
2. Backend clamps oversized input and redacts common secrets.
3. Language is detected from file extension or code shape.
4. Static analysis produces deterministic findings.
5. Optional external analyzers run when available: Pylint for Python and ESLint for JavaScript/TypeScript.
6. Review service calls the OpenAI Responses API with JSON Schema structured output, or demo mode if no key is configured.
7. The validated result is persisted as issues and test case suggestions.
8. The UI lets reviewers accept, ignore, or mark findings fixed.
9. Reports are exported as Markdown, PDF, or Word.

## Authentication And Authorization

The API uses signed bearer tokens and PBKDF2 password hashing for the open-source demo. Roles are:

- `developer`: create and view own tasks, update own review states.
- `reviewer`: view all tasks and update issue states.
- `tester`: update test case status.
- `admin`: manage users, prompt templates, and audit logs.

Production deployments should rotate `SECRET_KEY`, replace default users, and consider an external identity provider.

## Data Model

- `users`
- `review_tasks`
- `code_inputs`
- `review_issues`
- `test_cases`
- `prompt_templates`
- `audit_logs`

The current implementation stores code excerpts for review history. Production deployments should review retention policy before processing private repositories.

## AI Boundary

AI output is treated as a recommendation, not a final verdict. The API validates model output against a strict schema and exposes confidence values and human review states.

Prompt templates are administrator-managed and stored in `prompt_templates`; the latest enabled template is included in each review request.
