# Multi-stage build for production-grade optimization
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/

# Install python dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Production runner image
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime dependencies and Playwright platform dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv and app source from builder
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Set paths
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Install Playwright browser and dependencies inside container
RUN playwright install chromium
RUN playwright install-deps chromium

# Create directories for persistent volume storage
RUN mkdir -p /app/data /app/logs /app/downloads

# Volume for database persistence
VOLUME ["/app/data", "/app/logs", "/app/downloads"]

# Default entry point running the CLI main menu
ENTRYPOINT ["python", "src/interface/cli/main.py"]
