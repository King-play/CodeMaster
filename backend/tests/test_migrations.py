from pathlib import Path


def test_alembic_files_exist() -> None:
    assert Path("alembic.ini").exists()
    assert Path("migrations/env.py").exists()
    assert Path("migrations/versions/20260610_0001_initial_schema.py").exists()

