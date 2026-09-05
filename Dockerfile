FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# $PORT vem do próprio provedor (Railway injeta na hora do deploy); 8000 é só
# o fallback pra rodar o mesmo Dockerfile fora dele (docker run direto).
CMD ["./docker-entrypoint.sh"]
