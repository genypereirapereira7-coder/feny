from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse


def spa_index(request, *args, **kwargs):
    """Serve o `index.html` do React pra qualquer rota que não seja API/admin
    (ver `config/urls.py` — este é sempre o último padrão). Precisa existir
    porque o React Router usa rotas de verdade (`/clientes`, `/projetos/1`) —
    sem isto, dar F5 numa dessas URLs bateria direto no Django e devolveria
    404, já que ele não conhece essas rotas (só o JS do React conhece).
    `frontend_dist/` só existe dentro da imagem Docker (ver Dockerfile)."""
    index_path = settings.BASE_DIR / "frontend_dist" / "index.html"
    if not index_path.is_file():
        return HttpResponse(
            "Frontend não buildado nesta instância — ver frontend_dist/ no Dockerfile.",
            status=404, content_type="text/plain",
        )
    return HttpResponse(index_path.read_text(encoding="utf-8"))


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
