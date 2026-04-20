# =============================================================================
# Tripitaka MCP Server — Dockerfile (multi-stage, non-root)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: builder — ติดตั้ง dependencies ที่ต้อง compile
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# -----------------------------------------------------------------------------
# Stage 2: runtime — image ที่รันจริง (เล็กลง, ไม่มี build tools)
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:$PATH"

# เฉพาะ runtime lib ที่ psycopg2 ต้องใช้
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 app \
    && useradd  --system --uid 1001 --gid app --home /app --shell /sbin/nologin app

# Copy installed Python packages จาก builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy source code ด้วย ownership ของ user app
COPY --chown=app:app . .

USER app

# สร้าง cache dir ให้ app user เป็นเจ้าของ ก่อน volume mount
# (Docker volume init copy-up จะรักษา ownership นี้ตอน volume ว่างถูก mount ครั้งแรก)
# HF_HOME บังคับ path ชัดเจนไม่ต้องพึ่ง HOME env
RUN mkdir -p /app/.cache/huggingface
ENV HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

# Health check — ตรวจว่า Python import ได้
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import fastmcp" || exit 1

CMD ["python", "main.py"]
