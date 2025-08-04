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

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application with optimized concurrency settings
# --workers 4: CPU parallelism (1 worker per CPU core for I/O-bound workloads)
# --loop uvloop: 2-4x performance improvement over asyncio
# --worker-class uvicorn.workers.UvicornWorker: Optimized for ASGI
CMD ["uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop"]