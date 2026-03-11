"""Service-level endpoints for API metadata and health checks."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from redis import Redis
from redis.exceptions import RedisError

from automation.config.settings import settings

router = APIRouter(tags=["service"])


class ApiInfoResponse(BaseModel):
    message: str
    version: str
    status: str
    docs: str
    web_interface: str


class HealthLiveResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessDependency(BaseModel):
    status: str
    details: str | None = None


class HealthReadyResponse(BaseModel):
    status: str
    service: str
    version: str
    checks: dict[str, ReadinessDependency]


def _check_storage_ready() -> ReadinessDependency:
    try:
        for path_value in (settings.safe_storage_dir, settings.quarantine_dir):
            path = Path(path_value)
            path.mkdir(parents=True, exist_ok=True)
            if not path.is_dir():
                return ReadinessDependency(status="fail", details=f"Not a directory: {path}")
        return ReadinessDependency(status="ok")
    except OSError as exc:
        return ReadinessDependency(status="fail", details=str(exc))


def _check_sqlite_ready() -> ReadinessDependency:
    database_url = settings.database_url
    if not database_url.startswith("sqlite:///"):
        return ReadinessDependency(status="skip", details="Non-SQLite database URL")

    db_path = Path(database_url.replace("sqlite:///", ""))
    try:
        parent = db_path.parent if db_path.parent != Path("") else Path(".")
        parent.mkdir(parents=True, exist_ok=True)
        if not parent.is_dir():
            return ReadinessDependency(
                status="fail",
                details=f"DB parent is not a directory: {parent}",
            )
        return ReadinessDependency(status="ok")
    except OSError as exc:
        return ReadinessDependency(status="fail", details=str(exc))


def _check_redis_ready() -> ReadinessDependency:
    try:
        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            health_check_interval=0,
        )
        if client.ping():
            return ReadinessDependency(status="ok")
        return ReadinessDependency(status="fail", details="Ping returned falsy response")
    except RedisError as exc:
        return ReadinessDependency(status="fail", details=str(exc))
    except Exception as exc:
        return ReadinessDependency(status="fail", details=str(exc))


@router.get("/api", response_model=ApiInfoResponse)
async def api_info() -> ApiInfoResponse:
    return ApiInfoResponse(
        message="Email Automation Platform API",
        version=settings.app_version,
        status="running",
        docs="/docs",
        web_interface="/",
    )


@router.get("/health/live", response_model=HealthLiveResponse)
async def health_live() -> HealthLiveResponse:
    return HealthLiveResponse(
        status="alive",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get("/health", response_model=HealthLiveResponse)
async def health_compat() -> HealthLiveResponse:
    """Backward-compatible liveness endpoint."""
    return await health_live()


@router.get("/health/ready", response_model=HealthReadyResponse)
async def health_ready(response: Response) -> HealthReadyResponse:
    checks = {
        "storage": _check_storage_ready(),
        "sqlite": _check_sqlite_ready(),
        "redis": _check_redis_ready(),
    }
    overall_ok = all(item.status in {"ok", "skip"} for item in checks.values())
    overall_status = "ready" if overall_ok else "not_ready"
    response.status_code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthReadyResponse(
        status=overall_status,
        service=settings.app_name,
        version=settings.app_version,
        checks=checks,
    )
