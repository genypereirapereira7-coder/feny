#!/usr/bin/env bash
set -euo pipefail

# Restaura um dump gerado por backup_db.sh — sempre num banco NOVO, nunca
# sobrescreve o banco de origem por engano (ARCHITECTURE.md §18: "processo
# de restauração testado — não só 'existe uma cópia'"). Testar restauração
# regularmente, não só confiar que o backup existe, é o ponto inteiro deste
# script existir separado do backup_db.sh.
#
# Uso: ./scripts/restore_db.sh <arquivo.dump> <nome_do_banco_de_destino>

ARQUIVO="${1:?Uso: restore_db.sh <arquivo.dump> <nome_do_banco>}"
BANCO_DESTINO="${2:?Uso: restore_db.sh <arquivo.dump> <nome_do_banco>}"

createdb "$BANCO_DESTINO"
pg_restore --dbname="$BANCO_DESTINO" --no-owner "$ARQUIVO"

echo "Restaurado em: $BANCO_DESTINO"
