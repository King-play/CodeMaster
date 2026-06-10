# 🛡️ CodeMate

> 🚀 AI-assisted code review and test case generation, with human confirmation at the center. (o゜▽゜)o☆

CodeMate is an open-source web system for AI-assisted code review and test case suggestion. Users can submit code snippets, files, or Git diffs; the system redacts sensitive data, runs static analysis, asks an LLM or local demo reviewer for structured feedback, stores the result, supports human confirmation, and exports review reports.

It is built as a practical course project and a real GitHub-ready MVP: authentication, role-based access, audit logs, prompt templates, CI, CodeQL, Dependabot, Docker deployment, and database migrations are included.

## ✨ Highlights

- 🧩 Submit code snippets, files, or Git diffs for review
- 🛡️ Redact common secrets before model calls
- 🔍 Run built-in static checks plus optional Pylint and ESLint analyzers
- 🤖 Use OpenAI Responses API with JSON Schema structured output
- 🧪 Work in demo mode without an API key, great for local evaluation (｀・ω・´)
- 📌 Generate review issues with severity, line range, confidence, status, and suggestions
- ✅ Generate normal, boundary, exception, and security test case suggestions
- 👥 Support human states: `pending`, `accepted`, `ignored`, `fixed`
- ⚙️ Manage users, roles, prompt templates, and audit logs from the admin UI
- 📄 Export reports as Markdown, PDF, or Word
- 🚀 Ship with Docker, Nginx sample config, Alembic migrations, GitHub Actions, CodeQL, and Dependabot

## 🧱 Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, lucide-react |
| Backend | Python, FastAPI, SQLAlchemy, SQLite, OpenAI SDK |
| Static analysis | Built-in rules, Pylint, ESLint |
| Reports | Markdown, ReportLab PDF, python-docx |
| Database migration | Alembic |
| Quality | pytest, ESLint, GitHub Actions, CodeQL, Dependabot |

## 🚀 Quick Start

```bash
python -m venv .venv
cp .env.example .env
npm install
npm run install:all
npm run dev
```

Open:

- Web app: http://localhost:5173
- API docs: http://localhost:8000/docs

If you build the frontend and run the backend directly, the backend also serves the production UI:

```bash
npm run build:web
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000/.

## 🔐 Demo Accounts

Demo mode is enabled by default, so you can try the app without an OpenAI key. ヾ(≧▽≦*)o

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin123` | `admin` |
| `reviewer` | `reviewer123` | `reviewer` |
| `developer` | `developer123` | `developer` |

Change or remove these accounts before any public deployment.

## ⚙️ Configuration

Copy `.env.example` to `.env`, then edit values as needed.

| Variable | Description | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./data/codemate.db` |
| `SECRET_KEY` | Token signing key. Replace in production. | `change-this-in-production` |
| `OPENAI_API_KEY` | OpenAI API key for real AI review | empty |
| `OPENAI_MODEL` | Model used by the review service | `gpt-5-mini` |
| `CODEMATE_DEMO_MODE` | Use local heuristic review instead of an external model | `true` |
| `CODEMATE_ENABLE_EXTERNAL_ANALYZERS` | Enable Pylint/ESLint when available | `true` |
| `FRONTEND_ORIGIN` | CORS origin for the Vite app | `http://localhost:5173` |

To use OpenAI-backed review:

```env
OPENAI_API_KEY=your_api_key
CODEMATE_DEMO_MODE=false
```

## 🔌 Core API

- `GET /api/health`
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `POST /api/review-tasks`
- `GET /api/review-tasks`
- `GET /api/review-tasks/{task_id}`
- `PATCH /api/issues/{issue_id}`
- `PATCH /api/test-cases/{test_id}`
- `GET /api/review-tasks/{task_id}/report.md`
- `GET /api/review-tasks/{task_id}/report.pdf`
- `GET /api/review-tasks/{task_id}/report.docx`
- `GET /api/admin/users`
- `GET /api/admin/prompt-templates`
- `GET /api/admin/audit-logs`

## 🛠️ Development

```bash
npm run test
npm run lint:web
npm run build:web
npm audit --audit-level=high
npm --prefix frontend audit --audit-level=high
```

Useful database commands:

```bash
npm run db:upgrade
npm run db:stamp
npm run db:revision -- -m "describe change"
```

`db:stamp` is useful if you already created a local SQLite database before Alembic was introduced.

## 🐳 Docker

Single-container local demo:

```bash
docker compose up --build
```

Production-style reverse proxy:

```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up --build -d
```

The production compose file uses Nginx and a named SQLite volume. For a serious multi-user deployment, use Postgres, HTTPS, a real secret manager, and rotated credentials. Small steps, sturdy shoes. (ง •_•)ง

## 🗂️ Project Layout

```text
backend/             FastAPI app, auth, analysis, reporting, tests
frontend/            React + TypeScript UI
migrations/          Alembic migration scripts
docs/                Architecture, deployment, open-source checklist
deploy/              Nginx reverse proxy example
.github/             CI, CodeQL, Dependabot, issue and PR templates
```

## 🛡️ Security Notes

CodeMate follows the principle: AI assists, humans decide.

- Secrets are redacted before model calls where possible.
- API keys are never exposed to the frontend.
- Reports and review history may contain source-code excerpts; define retention rules before processing private repositories.
- Replace demo users and `SECRET_KEY` before deployment.
- Enable GitHub secret scanning and push protection in repository settings.

Please report vulnerabilities through the process described in [SECURITY.md](SECURITY.md).

## 🤝 Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and keep changes focused, tested, and easy to review. Good issues include sample input code, expected output, and actual output.

## 📚 References

- GitHub Docs: Community profile files and repository health guidance
- OpenAI API Docs: Responses API and Structured Outputs
- OWASP GenAI Security Project: LLM application risks
- NIST AI RMF and SSDF

## 📜 License

MIT. See [LICENSE](LICENSE).
