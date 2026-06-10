FROM node:22-bookworm AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY migrations/ migrations/
COPY alembic.ini alembic.ini
COPY --from=frontend /app/frontend/dist frontend/dist
COPY .env.example .env.example
EXPOSE 8000
CMD ["sh", "backend/start.sh"]
