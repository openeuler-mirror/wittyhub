FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

RUN pip install -i https://mirrors.aliyun.com/pypi/simple --no-cache-dir --default-timeout=300 -e .

COPY src ./src
COPY cli ./cli
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./

RUN mkdir -p /data/skills

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/api/v1/health').raise_for_status()"

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
