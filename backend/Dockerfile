FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True

WORKDIR /app

COPY backend/requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["sh", "-c", "exec uvicorn backend.fastapi_integration.main:app --host 0.0.0.0 --port ${PORT:-8000}"]