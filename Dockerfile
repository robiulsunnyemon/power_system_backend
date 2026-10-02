# ================================
# Stage 1: Builder
# ================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PRISMA_BINARY_CACHE_DIR=/root/.cache/prisma-python \
    DATABASE_URL="postgresql://placeholder:placeholder@localhost:5432/placeholder"

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install poetry and export plugin
RUN pip install --no-cache-dir poetry==2.1.2 poetry-plugin-export

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Export dependencies and install into virtualenv
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir urllib3==2.2.1

# Copy prisma schema and generate Prisma client & download engine binaries
COPY prisma/ ./prisma/
RUN python -m prisma generate && \
    # Remove nodeenv to prevent hundreds of megabytes of bloat, keeping only the query engine binaries
    rm -rf /root/.cache/prisma-python/nodeenv


# ================================
# Stage 2: Runtime
# ================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    PRISMA_BINARY_CACHE_DIR=/root/.cache/prisma-python

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment and Prisma engine binaries from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cache/prisma-python /root/.cache/prisma-python

# Copy the application source code
COPY app/ ./app/
COPY prisma/ ./prisma/
COPY scripts/ ./scripts/

# Expose the application port
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

