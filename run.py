#!/usr/bin/env python3
"""
Script to run the Email Automation Platform FastAPI server
"""
import sys
from pathlib import Path

# Add src directory to PYTHONPATH
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import uvicorn

from automation.config.settings import settings


def main():
    """Run FastAPI server using configured settings"""
    print(f"🚀 Starting Email Automation Platform on {settings.host}:{settings.port}")
    print(f"📚 API docs: http://{settings.host}:{settings.port}/docs")
    print(f"🔄 Debug mode: {settings.debug}")
    
    uvicorn.run(
        "automation.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        reload_dirs=["src"] if settings.debug else None,
        log_level="info"
    )


if __name__ == "__main__":
    main()