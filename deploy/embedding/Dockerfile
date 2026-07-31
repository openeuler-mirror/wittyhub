FROM python:3.11-slim

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null; \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/*.sources 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --default-timeout=300 \
    -i https://mirrors.aliyun.com/pypi/simple \
    fastapi \
    uvicorn \
    sentence-transformers \
    torch \
    numpy \
    pyyaml \
    huggingface_hub

COPY deploy/embedding/app.py /app/app.py

ENV PYTHONUNBUFFERED=1
ENV MODEL_NAME=BAAI/bge-base-zh-v1.5
ENV DIMENSION=768
ENV PORT=8082

EXPOSE 8082

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8082"]
