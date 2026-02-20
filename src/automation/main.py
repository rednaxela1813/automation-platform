"""
FastAPI application entry point для Email Automation Platform
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from automation.api.routers import router as api_router
from automation.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management для FastAPI приложения"""
    # Startup - создаем необходимые директории
    Path(settings.safe_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.quarantine_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 {settings.app_name} startup complete")
    yield
    # Shutdown
    print("📧 Email Automation Platform shutdown")


def create_app() -> FastAPI:
    """Factory функция для создания FastAPI приложения"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Автоматизация обработки электронной почты с вложениями",
        debug=settings.debug,
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Включаем роутеры
    app.include_router(api_router, prefix="/api/v1")

    return app


# Создаем экземпляр приложения
app = create_app()


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Email Automation Platform API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }