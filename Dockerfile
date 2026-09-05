# Estágio 1 — builda o React/Vite. Fica num serviço Railway só (mais simples
# que dois serviços + CORS): o Django do estágio 2 serve estes arquivos como
# estático, direto do mesmo domínio.
FROM node:20-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

# Mesmo domínio pra API e SPA por padrão (`/api/v1` relativo) — sem isso o
# frontend tentaria chamar `localhost:8000` mesmo rodando em produção. Só
# sobrescreva via `--build-arg` se um dia a API morar num domínio à parte.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Estágio 2 — Django, servindo a API e o `dist/` do estágio anterior.
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
COPY --from=frontend-build /frontend/dist ./frontend_dist
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# $PORT vem do próprio provedor (Railway injeta na hora do deploy); 8000 é só
# o fallback pra rodar o mesmo Dockerfile fora dele (docker run direto).
CMD ["./docker-entrypoint.sh"]
