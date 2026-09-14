from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse


# Prefixos que pertencem ao painel React. O resto do domínio é a vitrine —
# uma página estática (`landing/`) que não carrega React nenhum.
#
# As rotas antigas (`/clientes`, `/financeiro/...`) entram nesta lista mesmo
# tendo saído do menu: bookmark salvo antes da mudança precisa cair no bundle
# do painel, que é quem sabe redirecionar pra `/painel/...`. Sem isso o link
# antigo abriria a vitrine, que não tem a menor ideia do que fazer com ele.
ROTAS_DO_PAINEL = (
    "/painel",
    "/login",
    "/2fa",
    "/clientes",
    "/orcamentos",
    "/projetos",
    "/financeiro",
    "/documentos",
    "/suporte",
    "/equipe",
    "/configuracoes",
    "/auditoria",
)


# Páginas da vitrine que não são a raiz. Com e sem barra no fim porque as duas
# formas circulam por aí (link colado à mão, e-mail, QR code) e cair na home
# por causa de uma barra é perder a pessoa no meio do caminho.
#
# `/comecar.html` não entra: o arquivo existe em `frontend_dist/` e o
# WhiteNoise o entrega antes de qualquer view ser chamada. Funciona, só não
# passa por aqui — e por isso a prévia de link daquele endereço sai com
# caminho relativo. O endereço pra divulgar é o sem extensão.
PAGINAS_DA_VITRINE = {
    "/comecar": "comecar.html",
    "/comecar/": "comecar.html",
}


def spa_index(request, *args, **kwargs):
    """Serve a página certa pra qualquer rota que não seja API/admin (ver
    `config/urls.py` — este é sempre o último padrão).

    São duas páginas no mesmo deploy, e a rota decide qual:

    - `/painel/...`, `/login` e afins recebem `painel.html`, o `index.html` do
      build do React. O SPA usa rotas de verdade, então um F5 em
      `/painel/projetos/1` precisa cair aqui e devolver o app inteiro.
    - `/comecar` recebe `comecar.html`, a página de "começar um projeto"
      (formulário, serviços, etapas, investimento, projetos e dúvidas).
    - qualquer outra rota recebe `index.html`, a landing estática. Ela é a
      vitrine e não carrega uma linha do JavaScript do painel — que é o
      motivo de existir separada.

    Também completa as marcas de prévia de link (Open Graph): o HTML guarda a
    imagem como caminho relativo e aqui ela vira endereço absoluto montado a
    partir do host da requisição. WhatsApp e Facebook ignoram caminho
    relativo, e o domínio muda entre localhost, Railway e um domínio próprio —
    deixar um fixo no HTML seria escolher um dos três pra funcionar e
    descobrir os outros dois quebrados só quando alguém colasse o link.

    `frontend_dist/` só existe dentro da imagem Docker (ver Dockerfile).
    """
    if request.path.startswith(ROTAS_DO_PAINEL):
        nome = "painel.html"
    else:
        nome = PAGINAS_DA_VITRINE.get(request.path, "index.html")
    index_path = settings.BASE_DIR / "frontend_dist" / nome
    if not index_path.is_file():
        return HttpResponse(
            "Frontend não buildado nesta instância — ver frontend_dist/ no Dockerfile.",
            status=404, content_type="text/plain",
        )

    html = index_path.read_text(encoding="utf-8")
    origem = request.build_absolute_uri("/").rstrip("/")
    html = html.replace('content="/midia/og.jpg"', f'content="{origem}/midia/og.jpg"')

    # `og:url` é injetada aqui em vez de morar no HTML porque ela é a única
    # que muda de página pra página — é o endereço desta rota, não do site.
    # `request.path` sem a query string de propósito: a prévia do link com
    # `?utm_source=...` deve apontar pro mesmo lugar que o link sem ela.
    html = html.replace(
        "</head>",
        f'    <meta property="og:url" content="{request.build_absolute_uri(request.path)}" />\n  </head>',
        1,
    )
    return HttpResponse(html)


def health(request):
    """Checagem de vida usada por deploy e monitoramento (ARCHITECTURE.md
    §18, Fase 10 — observabilidade). Confere a conexão com o banco de
    verdade: sem isto, um deploy com banco fora do ar reportaria "ok" do
    mesmo jeito, porque a aplicação em si respondeu."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except OperationalError:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)

    return JsonResponse({"status": "ok", "database": "ok"})
