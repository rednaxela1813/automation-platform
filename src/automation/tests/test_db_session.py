from __future__ import annotations

from sqlalchemy.engine import Engine

from automation.db.session import create_engine_from_settings, normalize_database_url


def test_normalize_database_url_converts_postgresql_scheme():
    assert (
        normalize_database_url("postgresql://user:pass@localhost:5432/app")
        == "postgresql+psycopg://user:pass@localhost:5432/app"
    )


def test_normalize_database_url_converts_postgres_scheme():
    assert (
        normalize_database_url("postgres://user:pass@localhost:5432/app")
        == "postgresql+psycopg://user:pass@localhost:5432/app"
    )


def test_normalize_database_url_keeps_sqlite_unchanged():
    assert normalize_database_url("sqlite:///tmp/test.db") == "sqlite:///tmp/test.db"


def test_create_engine_from_settings_builds_sqlite_engine(tmp_path):
    engine = create_engine_from_settings(f"sqlite:///{tmp_path / 'test.db'}")

    assert isinstance(engine, Engine)
    assert str(engine.url).startswith("sqlite:///")
