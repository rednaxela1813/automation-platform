from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from automation.config.settings import settings


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def create_engine_from_settings(database_url: str | None = None) -> Engine:
    resolved_url = normalize_database_url(database_url or settings.database_url)
    connect_args = {"check_same_thread": False} if resolved_url.startswith("sqlite") else {}
    return create_engine(resolved_url, future=True, pool_pre_ping=True, connect_args=connect_args)
