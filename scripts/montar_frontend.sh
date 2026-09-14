#!/bin/sh
# Monta `frontend_dist/` — o único diretório que o Django serve como estático.
#
# São duas páginas no mesmo deploy e elas vêm de lugares diferentes:
#
#   landing/            → a vitrine (`/`), HTML e CSS puros, sem build
#   frontend/dist/      → o painel (`/painel`), build do React/Vite
#
# O `index.html` do React vira `painel.html` pra a raiz ficar livre pra
# vitrine. Quem escolhe qual entregar é `apps/core/views.py::spa_index`.
#
# Uso:
#   ./scripts/montar_frontend.sh            # local, depois de `npm run build`
#   ./scripts/montar_frontend.sh _dist      # Docker, com o dist já copiado
set -e

cd "$(dirname "$0")/.."

DIST="${1:-frontend/dist}"

if [ ! -f "$DIST/index.html" ]; then
  echo "Build do React não encontrado em $DIST — rode 'npm run build' em frontend/ primeiro." >&2
  exit 1
fi

rm -rf frontend_dist
cp -R "$DIST" frontend_dist
mv frontend_dist/index.html frontend_dist/painel.html

# A landing por último, inteira: se um dia os dois tiverem um arquivo de mesmo
# nome, é a vitrine que ganha a raiz do domínio. Copiar a pasta toda (e não uma
# lista de arquivos) é o que evita o erro clássico de acrescentar uma página
# nova e descobrir no deploy que ela ficou de fora.
cp landing/* frontend_dist/

echo "frontend_dist/ montado: vitrine em index.html, painel em painel.html"
