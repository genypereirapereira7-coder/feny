from django.db import connection
from django.db.utils import OperationalError
from django.http import JsonResponse


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
