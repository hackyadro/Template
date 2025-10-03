FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    openssl \
    mosquitto-clients \
    mosquitto \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for certificates and logs
RUN mkdir -p certs logs

# Set permissions
RUN chmod +x generate_certs.py

# Expose port
EXPOSE 8000

# Health check that works for HTTP or HTTPS
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import os, ssl, urllib.request;\nurl_https='https://localhost:8000/health'; url_http='http://localhost:8000/health';\ntry:\n    ctx=ssl._create_unverified_context();\n    urllib.request.urlopen(urllib.request.Request(url_https), context=ctx, timeout=10);\n    raise SystemExit(0)\nexcept Exception:\n    pass\ntry:\n    urllib.request.urlopen(url_http, timeout=10);\n    raise SystemExit(0)\nexcept Exception:\n    raise SystemExit(1)"

# Run the application via launcher (supports TLS)
CMD ["python", "run.py", "--no-reload"]