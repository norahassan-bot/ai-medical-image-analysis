# =============================================================================
# AI Medical Image Analysis - Backend Dockerfile
# Python 3.11 + FastAPI + PyTorch + Torchvision + OpenCV + SQLite Persistence
# =============================================================================

FROM python:3.11-slim AS runtime

# Set environment variables for Python in container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=production \
    PORT=8000 \
    HOST=0.0.0.0

# Install necessary OS libraries for OpenCV headless, Pillow, and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group for security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-create runtime directories and set ownership
RUN mkdir -p /app/data/visualizations /app/reports/pdf /app/models && \
    chown -R appuser:appgroup /app

# Copy application source code
COPY --chown=appuser:appgroup api /app/api
COPY --chown=appuser:appgroup database /app/database
COPY --chown=appuser:appgroup reports /app/reports
COPY --chown=appuser:appgroup src /app/src
COPY --chown=appuser:appgroup models /app/models

# Switch to non-root user
USER appuser

# Expose FastAPI backend port
EXPOSE 8000

# Healthcheck to verify FastAPI service and model readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').getcode() == 200 else 1)" || exit 1

# Production startup command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
