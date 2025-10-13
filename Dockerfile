# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /code

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

# Install system dependencies (including curl for health check)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY pytest.ini .

# Create logs directory and set permissions
RUN mkdir -p logs

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --shell /bin/bash appuser

# Set proper ownership and permissions
RUN chown -R appuser:appuser /code && chmod -R 755 /code/logs

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/status/ || exit 1

# Start the application with multiple workers for production
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
