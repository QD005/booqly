# ── Dockerfile ───────────────────────────────────────────────────────────────
# Use official Python image (slim = smaller size)
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (needed for PostgreSQL)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies FIRST (Docker caches this layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Create logs directory (fixes the logging error you had)
RUN mkdir -p /app/logs

# Collect static files during build
RUN python manage.py collectstatic --noinput

# Expose port 8000 for Gunicorn
EXPOSE 8000

# Default command: run Gunicorn with 3 workers
CMD ["gunicorn", "server.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
