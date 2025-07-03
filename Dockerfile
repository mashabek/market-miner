# Build stage for Python dependencies
FROM python:3.11-slim as builder

# Set a non-interactive frontend for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies with --no-install-recommends and cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-dev \
    python3-pip \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies with --no-install-recommends and cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 && \
    rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Set working directory
WORKDIR /app

# Copy Scrapy project files
COPY scrapy.cfg .
COPY scrapper ./scrapper/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV SCRAPY_SETTINGS_MODULE=scrapper.settings

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# The entrypoint script will be provided by Cloud Run job
ENTRYPOINT ["python", "-m", "scrapy", "crawl"]