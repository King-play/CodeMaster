# Deployment

## Local Development

```bash
cp .env.example .env
npm install
npm run install:all
npm run dev
```

## Production Checklist

- Set `CODEMATE_DEMO_MODE=false`.
- Set `OPENAI_API_KEY`.
- Replace `SECRET_KEY`.
- Replace or remove the default demo users.
- Use a managed database instead of local SQLite for multi-user deployments.
- Add authentication and project-level authorization.
- Put the API behind HTTPS.
- Configure CORS for the production frontend origin.
- Define log retention and code retention policy.
- Run `npm run db:upgrade` after deploying a new schema.
- If you already created a local SQLite database before Alembic was added, run `npm run db:stamp` once to mark the current schema as migrated.

## Static Frontend Build

```bash
npm --prefix frontend run build
```

Deploy `frontend/dist` to any static hosting provider and route `/api/*` to the FastAPI service.

## Docker Compose

Local single-container demo:

```bash
docker compose up --build
```

Production-style reverse proxy:

```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up --build -d
```

The production compose file uses Nginx as a reverse proxy and stores SQLite data in a named volume. For serious multi-user deployments, replace SQLite with Postgres and keep `OPENAI_API_KEY` in the platform's secret manager.

## Platform Notes

- Render, Railway, Fly.io, and similar platforms can build the provided Dockerfile directly.
- Set the service port to `8000` unless the platform injects its own `PORT`; in that case update the Docker command.
- Store `.env` values as platform secrets, not committed files.
- Run Alembic migrations during release, for example `python -m alembic upgrade head`.
