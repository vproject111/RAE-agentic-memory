# RAE Universal Dockerfile
# Supports both CPU (Lite) and GPU (Full) via build arguments

ARG BASE_IMAGE=python:3.14-slim
FROM ${BASE_IMAGE} AS builder

# Set build environment
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    curl git gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtualenv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install local RAE packages FIRST
# (Order matters for dependency resolution)
COPY sdk/python/rae_memory_sdk /app/sdk/python/rae_memory_sdk
RUN pip install --no-cache-dir /app/sdk/python/rae_memory_sdk

COPY rae-core /app/rae-core
RUN pip install --no-cache-dir /app/rae-core

COPY rae_adapters /app/rae_adapters
RUN pip install --no-cache-dir /app/rae_adapters

# Install application requirements
COPY apps/memory_api/requirements-base.txt /app/requirements-base.txt
RUN pip install --no-cache-dir -r /app/requirements-base.txt

# Optional: Full ML features (if GPU build is requested, you might want these)
ARG INSTALL_ML=false
COPY apps/memory_api/requirements-ml.txt /app/requirements-ml.txt
RUN if [ "$INSTALL_ML" = "true" ] ; then pip install --no-cache-dir -r /app/requirements-ml.txt ; fi

# FINAL STAGE
FROM ${BASE_IMAGE} AS runtime

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    curl libpq5 procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY apps /app/apps
COPY models /app/models

# Setup user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "apps.memory_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
