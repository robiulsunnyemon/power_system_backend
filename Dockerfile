# ================================
# Stage 1: Builder
# ================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry and plugin
RUN pip install poetry==2.1.2 poetry-plugin-export

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Export dependencies and install them
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes && \
    pip install --target=/app/package -r requirements.txt && \
    pip install --target=/app/package urllib3==2.2.1 prisma


# ================================
# Stage 2: Runtime
# ================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/package \
    PATH="/app/package/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy packages from builder
COPY --from=builder /app/package /app/package
# Copy the application source code
COPY app/ ./app/
COPY prisma/ ./prisma/

# Generate Prisma client (using the installed package)
RUN python -m prisma generate

# Expose the application port
EXPOSE 8000

# Run the FastAPI application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
