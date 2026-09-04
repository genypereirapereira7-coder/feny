"""Única camada que fala HTTP com a Evolution API
(ARCHITECTURE.md §6.9: "Nenhum outro app importa `whatsapp` diretamente").

A Evolution API é open-source e tem builds/versões com contrato de payload
ligeiramente diferente entre si (o endpoint `/message/sendText/{instance}` e
o header `apikey` são estáveis entre versões comuns; o formato exato do corpo
JSON pode variar). `_montar_corpo` é a única função que sabe a forma desse
corpo — se a instância da Feny usar uma variação diferente, o ajuste é uma
linha aqui, não uma mudança em `apps.notifications` ou em quem chama `send()`.
"""

import re

import requests
from django.conf import settings

from apps.whatsapp.exceptions import EvolutionApiError

_TIMEOUT_SEGUNDOS = 10


def _somente_digitos(numero: str) -> str:
    return re.sub(r"\D", "", numero)


def _montar_corpo(numero: str, texto: str) -> dict:
    return {"number": _somente_digitos(numero), "text": texto}


def _configuracao() -> tuple[str, str, str]:
    base_url = settings.EVOLUTION_API_BASE_URL
    api_key = settings.EVOLUTION_API_KEY
    instance = settings.EVOLUTION_API_INSTANCE
    if not (base_url and api_key and instance):
        raise EvolutionApiError("Evolution API não está configurada neste ambiente.")
    return base_url, api_key, instance


def send_text(numero: str, texto: str) -> dict:
    base_url, api_key, instance = _configuracao()

    try:
        resposta = requests.post(
            f"{base_url}/message/sendText/{instance}",
            json=_montar_corpo(numero, texto),
            headers={"apikey": api_key, "Content-Type": "application/json"},
            timeout=_TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.RequestException as exc:
        raise EvolutionApiError(f"Falha de rede ao enviar WhatsApp para {numero}: {exc}") from exc

    if not resposta.ok:
        raise EvolutionApiError(f"Evolution API recusou o envio para {numero}: {resposta.status_code} {resposta.text}")
    return resposta.json()
