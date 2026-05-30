FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Healthcheck
HEALTHCHECK --interval=15s --timeout=10s --start-period=30s --retries=8 \
    CMD curl -sf http://localhost:8000/health || exit 1

# Start with uvicorn
# Note: --reload removed. It causes 504s because WatchFiles triggers on
# sentence-transformers model downloads. Use docker compose restart backend
# to pick up code changes during development.
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info", \
     "--timeout-keep-alive", "120", \
     "--access-log"]
