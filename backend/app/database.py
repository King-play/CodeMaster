from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


settings = get_settings()

if settings.db_path is not None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from sqlalchemy import select

    from . import models
    from .auth import hash_password

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_migrations()
    with SessionLocal() as db:
        if db.scalar(select(models.User).limit(1)) is None:
            db.add_all(
                [
                    models.User(
                        username="admin",
                        password_hash=hash_password("admin123"),
                        role=models.UserRole.admin.value,
                    ),
                    models.User(
                        username="reviewer",
                        password_hash=hash_password("reviewer123"),
                        role=models.UserRole.reviewer.value,
                    ),
                    models.User(
                        username="developer",
                        password_hash=hash_password("developer123"),
                        role=models.UserRole.developer.value,
                    ),
                ]
            )
        if db.scalar(select(models.PromptTemplate).limit(1)) is None:
            db.add(
                models.PromptTemplate(
                    name="default-review-standard",
                    template=(
                        "Review for correctness, boundary cases, exception handling, "
                        "security risk, maintainability, and missing tests. Prefer "
                        "evidence-backed findings over broad style advice."
                    ),
                    version="1.0.0",
                    enabled=1,
                )
            )
        db.commit()


def _apply_sqlite_migrations() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "review_tasks" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("review_tasks")}
        if "user_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE review_tasks ADD COLUMN user_id INTEGER"))
    if "audit_logs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("audit_logs")}
        if "user_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE audit_logs ADD COLUMN user_id INTEGER"))
