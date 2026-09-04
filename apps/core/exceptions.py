from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """Erro de regra de negócio. Services levantam isto — não `Exception` genérica
    nem `ValueError` solto — pra que a camada de API saiba diferenciar "a regra
    recusou" de "o código quebrou" (ver ARCHITECTURE.md §21)."""


def custom_exception_handler(exc, context):
    """Traduz `DomainError` pra 400 automaticamente, em qualquer view da API.

    Sem isto, cada view que chama um service teria que lembrar de fazer o
    próprio try/except — uma fonte de verdade a menos, exatamente o que
    ARCHITECTURE.md §21 pede pra evitar.
    """
    if isinstance(exc, DomainError):
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return drf_exception_handler(exc, context)
