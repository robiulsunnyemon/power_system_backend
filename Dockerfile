# ================================
# Stage 1: Builder
# ================================
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry and the export plugin
RUN pip install poetry==2.1.2 poetry-plugin-export

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Export dependencies to requirements.txt (without dev deps)
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Install dependencies into a virtual environment
RUN pip install --prefix=/install -r requirements.txt


# ================================
# Stage 2: Runtime
# ================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy the application source code
COPY app/ ./app/
COPY prisma/ ./prisma/

# Generate Prisma client
RUN pip install prisma && prisma generate

# Expose the application port
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
