# ==============================================================================
# Dockerfile — MAT-VLAB Production Container
# Lightweight, secure, non-root Python 3.12 container running Gunicorn WSGI
# ==============================================================================
FROM python:3.12-slim

# Standard Python environment settings for containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp \
    PORT=5000 \
    HOST=0.0.0.0 \
    FLASK_ENV=production

# System libraries for numerical rendering & fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    libpng-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user for security
RUN groupadd -r matvlab && useradd -r -g matvlab -d /app -s /sbin/nologin matvlab

WORKDIR /app

# Cache dependency layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure data directories exist and assign permissions
RUN mkdir -p data/uploads && chown -R matvlab:matvlab /app

# Switch to non-root user
USER matvlab

# Expose HTTP port
EXPOSE 5000

# Healthcheck to verify server is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run with Gunicorn WSGI server
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
