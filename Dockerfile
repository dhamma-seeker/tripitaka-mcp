# =============================================================================
# Tripitaka MCP Server — Dockerfile
# =============================================================================

FROM python:3.12-slim

# ติดตั้ง system dependencies ที่จำเป็น
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ตั้ง working directory
WORKDIR /app

# คัดลอกและติดตั้ง Python dependencies ก่อน (ใช้ Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอก source code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import fastmcp; print('ok')" || exit 1

# รัน MCP Server
CMD ["python", "main.py"]
