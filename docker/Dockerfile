FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=app.settings

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY app/ .
COPY scripts/ scripts/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application with optimized concurrency settings for 5000+ connections
# --workers 16: Optimized worker count for high concurrency
# --backlog 20000: Large connection queue for handling bursts
# --limit-concurrency 6000: Maximum concurrent connections per process
# --loop uvloop: 2-4x performance improvement over asyncio
# --worker-connections 1000: Connections per worker process
CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "16", "--backlog", "20000", "--limit-concurrency", "6000", "--loop", "uvloop", "--worker-connections", "1000"]