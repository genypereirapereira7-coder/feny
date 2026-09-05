#!/bin/sh
# Roda a cada deploy (Railway/Render/qualquer PaaS baseado neste Dockerfile):
# migração e estático são responsabilidade do próprio container subindo, não
# de um passo manual separado que alguém pode esquecer de rodar.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
