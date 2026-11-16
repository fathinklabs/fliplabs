# ============================================================================
# FlipLabs Containerfile (Lightweight Multi-Core PDF Flipbook Server)
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY converter/requirements.txt /app/converter/requirements.txt
RUN pip install --no-cache-dir -r /app/converter/requirements.txt

COPY . /app

# Ensure directories exist
RUN mkdir -p /app/books /app/server/uploads

EXPOSE 8080

# Lightweight single-worker uvicorn to keep RAM usage < 80MB on srv-lmslabs-smpjkt
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
