FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
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
    huggingface_hub

COPY deploy/docker/embedding_service.py /app/embedding_service.py

ENV PYTHONUNBUFFERED=1
ENV MODEL_NAME=BAAI/bge-base-zh-v1.5
ENV DIMENSION=768
ENV PORT=8081

EXPOSE 8081

CMD ["uvicorn", "embedding_service:app", "--host", "0.0.0.0", "--port", "8081"]
