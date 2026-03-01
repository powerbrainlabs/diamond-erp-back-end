FROM python:3.9-alpine

WORKDIR /app

# Install system dependencies (minimal for Alpine)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
# --no-cache-dir: don't store cache
# --disable-pip-version-check: skip version check (faster)
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application with single worker for low memory usage
# Using --workers 1 would spawn multiple processes, so we use single process mode
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--limit-concurrency", "100", "--timeout-keep-alive", "5"]

