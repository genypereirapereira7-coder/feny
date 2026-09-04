"""Validação de CPF/CNPJ pelo dígito verificador — não só formato/tamanho.

O backend nunca confia que o frontend validou (ARCHITECTURE.md §46): um CPF
com 11 dígitos plausíveis mas dígito verificador errado é rejeitado aqui,
antes de qualquer coisa tocar o banco.
"""

import re


def somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def validar_cpf(valor: str) -> bool:
    cpf = somente_digitos(valor)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def _digito(base: str) -> int:
        tamanho = len(base)
        soma = sum(int(d) * (tamanho + 1 - i) for i, d in enumerate(base))
        resto = (soma * 10) % 11
        return resto if resto < 10 else 0

    if _digito(cpf[:9]) != int(cpf[9]):
        return False
    return _digito(cpf[:10]) == int(cpf[10])


def validar_cnpj(valor: str) -> bool:
    cnpj = somente_digitos(valor)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    def _digito(base: str, pesos: list[int]) -> int:
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    if _digito(cnpj[:12], pesos_1) != int(cnpj[12]):
        return False
    return _digito(cnpj[:13], pesos_2) == int(cnpj[13])
