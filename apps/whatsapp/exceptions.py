class EvolutionApiError(Exception):
    """Falha ao falar com a Evolution API (rede, HTTP não-2xx, instância
    desconectada). Não é `DomainError` — quem trata isso é
    `apps.notifications.services.dispatch_pending`, marcando a notificação
    como falhada e reprocessando depois; nunca deve derrubar a transação que
    originou o aviso (ARCHITECTURE.md §11, spec técnica §59)."""
