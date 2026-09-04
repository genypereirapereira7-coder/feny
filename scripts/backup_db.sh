#!/usr/bin/env bash
set -euo pipefail

# Backup do PostgreSQL (ARCHITECTURE.md §18). Formato custom (-Fc): permite
# restauração seletiva (só uma tabela, por exemplo) e é o formato que a
# própria documentação do Postgres recomenda para isso, em vez de um dump
# em texto puro.
#
# Uso: ./scripts/backup_db.sh [arquivo_de_saida]
# Lê DATABASE_URL do ambiente — a mesma variável que o Django já usa.

DESTINO="${1:-backup_$(date +%Y%m%d_%H%M%S).dump}"

pg_dump --format=custom --file="$DESTINO" "$DATABASE_URL"

echo "Backup salvo em: $DESTINO"
