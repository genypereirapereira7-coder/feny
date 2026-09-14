"""Webhook do agente de IA do WhatsApp (Typebot + Evolution API).

Fica em `views.py`, e não em `api/views.py`, porque não é DRF: o Typebot posta
JSON cru e espera JSON cru de volta, sem negociação de conteúdo, sem
paginação e sem autenticação por token de usuário. Enfiar isso num `APIView`
seria pagar o preço de um framework pra não usar nada dele.

É a **segunda** porta da plataforma aberta pra internet (a primeira é o
formulário do site, em `api/views.py`). Toda porta dessas tem que responder
três perguntas antes de escrever no banco: quem está batendo, o que veio, e o
que acontece se a mesma coisa vier duas vezes. Nesta ordem, aqui:

1. **Quem** — segredo combinado no cabeçalho `X-Webhook-Token`. Sem ele,
   qualquer pessoa com o endereço poderia cadastrar negócio fechado.
2. **O quê** — o JSON é lido com tolerância (o Typebot muda o formato conforme
   o bloco que dispara o webhook) e o telefone é validado de verdade.
3. **Duas vezes** — o telefone é único e a escrita é `update_or_create`: a
   mesma conversa reenviada atualiza o registro em vez de duplicar.
"""

import hmac
import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.leads.models import ClientePotencial
from apps.leads.validators import normalizar_telefone, telefone_valido

logger = logging.getLogger(__name__)

PALAVRA_DE_FECHAMENTO = "[FECHADO]"

# Nomes aceitos pra cada campo. O Typebot entrega as variáveis do fluxo com o
# nome que a pessoa deu a elas, e o fluxo costuma ser escrito em português
# enquanto os exemplos da documentação estão em inglês — aceitar os dois evita
# que renomear uma variável no Typebot derrube a integração em silêncio.
CAMPOS = {
    "nome": ("nome", "name", "nome_cliente", "cliente"),
    "telefone": ("telefone", "phone", "whatsapp", "numero", "number"),
    "descricao_projeto": ("descricao_projeto", "descricao", "projeto", "description", "message"),
    "valor_estimado": ("valor_estimado", "valor", "amount", "price", "orcamento"),
}


@csrf_exempt
@require_POST
def webhook_whatsapp_ia(request):
    """Recebe o fim de uma conversa fechada pelo agente e cadastra o contato.

    Responde sempre em JSON e sempre rápido: o Typebot trata resposta lenta ou
    corpo inesperado como falha e repete o envio, e repetição aqui é conversa
    duplicada na fila de atendimento.
    """
    if not _token_confere(request):
        # 401 e não 403: o que falta é credencial, não permissão. E a mensagem
        # não diz se o token está errado ou ausente — quem está sondando o
        # endereço não ganha pista de qual dos dois é.
        return JsonResponse({"detail": "Não autorizado."}, status=401)

    try:
        corpo = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Corpo não é JSON válido."}, status=400)

    if not isinstance(corpo, dict):
        return JsonResponse({"detail": "Esperado um objeto JSON."}, status=400)

    if PALAVRA_DE_FECHAMENTO not in _achatar(corpo):
        # Conversa ainda andando. 200 de propósito: não é erro, e devolver
        # erro faria o Typebot reenviar a mesma mensagem em laço.
        return JsonResponse({"detail": "Sem fechamento nesta mensagem.", "salvo": False}, status=200)

    dados = _extrair(corpo)

    telefone = normalizar_telefone(dados.get("telefone") or "")
    if not telefone_valido(telefone):
        logger.warning("webhook-ia: telefone inválido ou ausente no fechamento")
        return JsonResponse({"detail": "Telefone ausente ou inválido."}, status=400)

    nome = (dados.get("nome") or "").strip()
    descricao = (dados.get("descricao_projeto") or "").strip()
    if not nome or not descricao:
        return JsonResponse({"detail": "Nome e descrição do projeto são obrigatórios."}, status=400)

    cliente, criado = ClientePotencial.objects.update_or_create(
        telefone=telefone,
        defaults={
            "nome": nome[:150],
            "descricao_projeto": descricao,
            "valor_estimado": _valor(dados.get("valor_estimado")),
        },
    )

    logger.info("webhook-ia: fechamento %s para %s", "criado" if criado else "atualizado", telefone)
    return JsonResponse(
        {"detail": "Fechamento registrado.", "salvo": True, "criado": criado, "id": str(cliente.id)},
        status=201 if criado else 200,
    )


def _token_confere(request) -> bool:
    """Compara o segredo em tempo constante.

    `compare_digest` e não `==`: comparação normal de string vaza, pelo tempo
    que leva, quantos caracteres do início bateram — e com isso um token pode
    ser descoberto caractere a caractere.

    Sem `WHATSAPP_IA_WEBHOOK_TOKEN` configurado, o webhook recusa tudo. Falhar
    fechado é a escolha certa numa porta aberta pra internet: um deploy onde
    alguém esqueceu a variável fica sem integração, que é um problema visível,
    em vez de ficar sem tranca, que é um problema invisível.
    """
    esperado = getattr(settings, "WHATSAPP_IA_WEBHOOK_TOKEN", "")
    if not esperado:
        logger.error("webhook-ia: WHATSAPP_IA_WEBHOOK_TOKEN não configurado — recusando tudo")
        return False

    recebido = request.headers.get("X-Webhook-Token", "")
    return hmac.compare_digest(recebido, esperado)


def _achatar(valor) -> str:
    """Todo o conteúdo do payload como um texto só, pra procurar a palavra.

    O Typebot manda o fechamento em lugares diferentes conforme o bloco que
    dispara o webhook — às vezes numa variável do fluxo, às vezes no texto da
    última mensagem, às vezes dentro de uma lista de mensagens. Procurar só
    numa chave esperada é a forma de a integração quebrar quando alguém mexer
    no fluxo sem avisar.
    """
    if isinstance(valor, dict):
        return " ".join(_achatar(v) for v in valor.values())
    if isinstance(valor, (list, tuple)):
        return " ".join(_achatar(v) for v in valor)
    return str(valor)


def _extrair(corpo: dict) -> dict:
    """Pega os campos onde quer que o Typebot os tenha colocado.

    Procura no objeto de fora e nos lugares onde o Typebot costuma aninhar as
    variáveis do fluxo. Um nível de profundidade basta e é proposital: varrer
    o payload inteiro acharia, por exemplo, o telefone de dentro de um bloco
    de metadados do provedor e cadastraria a pessoa errada.
    """
    fontes = [corpo]
    for chave in ("variables", "data", "payload", "resultado", "result"):
        aninhado = corpo.get(chave)
        if isinstance(aninhado, dict):
            fontes.append(aninhado)

    achados = {}
    for destino, nomes in CAMPOS.items():
        for fonte in fontes:
            for nome in nomes:
                valor = fonte.get(nome)
                if valor not in (None, ""):
                    achados[destino] = valor
                    break
            if destino in achados:
                break
    return achados


def _valor(bruto) -> Decimal | None:
    """Converte o valor estimado, aceitando o que o robô costuma mandar.

    "R$ 12.500,00", "12500.00" e 12500 chegam todos aqui. Valor que não dá pra
    ler vira `None` em vez de derrubar o cadastro: o fechamento continua
    valendo sem o número, e quem atender pergunta.
    """
    if bruto in (None, ""):
        return None

    if isinstance(bruto, (int, float, Decimal)):
        texto = str(bruto)
    else:
        texto = str(bruto)
        # Tira tudo que não é dígito, vírgula ou ponto; depois resolve o
        # formato brasileiro (1.234,56) virando o formato que o Decimal lê.
        texto = "".join(c for c in texto if c.isdigit() or c in ",.")
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")

    try:
        valor = Decimal(texto)
    except (InvalidOperation, ValueError):
        logger.warning("webhook-ia: valor estimado ilegível (%r) — salvando sem valor", bruto)
        return None

    return valor if valor > 0 else None
