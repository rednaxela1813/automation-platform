# Dockerfile for Email Automation Platform
FROM python:3.13-slim AS base

ARG INSTALL_DEV=false

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ src/
COPY run.py ./
COPY templates/ templates/

# Install Python dependencies
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install --no-cache-dir -e ".[dev]"; \
    else \
        pip install --no-cache-dir -e .; \
    fi

# Create storage directories
RUN mkdir -p storage/safe storage/quarantine logs

# Create non-root user
RUN groupadd -r automation && useradd -r -g automation automation
RUN chown -R automation:automation /app
USER automation

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python", "run.py"]
