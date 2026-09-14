"""Validação dos campos que chegam do formulário público do site.

Este é o único endpoint da plataforma aberto pra internet inteira, sem login
nenhum atrás — então aqui a validação não é só conveniência de UX, é o portão.
O formulário do site valida os mesmos campos na tela (ver
`frontend/src/routes/site/validacao.ts`), mas essa camada existe pro visitante
enxergar o erro antes de enviar; quem decide o que entra no banco é isto aqui.
"""

import re

# Reaproveita o normalizador de `customers` em vez de reescrever o mesmo
# `re.sub` — `leads` já depende de `customers` (o lead convertido aponta pra
# um Customer), então não é acoplamento novo.
from apps.customers.validators import somente_digitos

__all__ = ["somente_digitos", "normalizar_telefone", "telefone_valido", "tem_letra"]


def normalizar_telefone(valor: str) -> str:
    """Guarda só dígitos, sem o +55 — a formatação é problema de exibição.

    Mesmo critério do `Customer.document`: o banco guarda o valor cru e a tela
    formata. Um número colado de WhatsApp ("+55 (71) 99999-8888") chega aqui
    com 13 dígitos; os dois primeiros são o código do país e não fazem parte
    do telefone em si.
    """
    digitos = somente_digitos(valor)
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    return digitos


def telefone_valido(valor: str) -> bool:
    """Telefone brasileiro de verdade: DDD existente + 8 ou 9 dígitos.

    `len(...) >= 10` sozinho aceitaria "0000000000". Os DDDs brasileiros vão
    de 11 a 99 mas nem todo número nessa faixa existe — a checagem abaixo
    recusa os que começam com 0 e os terminados em 0, que não são DDD em
    lugar nenhum. Celular (11 dígitos) obrigatoriamente começa com 9 depois
    do DDD desde a migração de 2016.
    """
    digitos = normalizar_telefone(valor)
    if len(digitos) not in (10, 11):
        return False

    ddd = digitos[:2]
    if ddd[0] == "0" or ddd[1] == "0":
        return False

    numero = digitos[2:]
    if len(numero) == 9 and numero[0] != "9":
        return False
    # Fixo nunca começa com 0 ou 1 (esses prefixos são serviço/operadora).
    if len(numero) == 8 and numero[0] in "01":
        return False

    return True


def tem_letra(valor: str) -> bool:
    """Recusa "123", "...", "   " num campo que deveria ser texto de gente."""
    return bool(re.search(r"[^\W\d_]", valor or "", flags=re.UNICODE))
