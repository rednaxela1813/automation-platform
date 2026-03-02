"""Top-level API router that aggregates endpoint modules."""

from __future__ import annotations

from fastapi import APIRouter

from automation.api.endpoints.emails import router as emails_router
from automation.api.endpoints.files import router as files_router
from automation.api.endpoints.system import router as system_router

router = APIRouter()
router.include_router(emails_router)
router.include_router(files_router)
router.include_router(system_router)
