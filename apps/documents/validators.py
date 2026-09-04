"""Validação de upload — ARCHITECTURE.md §35, §13 (Fase 10).

Cobre tamanho, extensão e agora também os bytes de verdade (magic number) —
o `content_type` do upload vem do header HTTP que o próprio cliente manda,
então nunca foi prova de nada, só pista; a extensão sozinha também não é
prova (um `.exe` renomeado pra `.pdf` passa na checagem de nome). Os dois
ајuntos + o conteúdo real são a defesa em profundidade.
"""

import os

from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20MB

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx", ".txt"}

# Assinatura (magic number) esperada no início do arquivo, por extensão.
# `.txt` fica de fora de propósito: texto puro não tem assinatura binária
# confiável — tamanho + extensão continuam sendo o limite prático ali, e
# isso é uma limitação conhecida, não um descuido.
_ASSINATURAS_POR_EXTENSAO = {
    ".pdf": (b"%PDF",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    # OOXML (docx/xlsx) é um ZIP por dentro — mesma assinatura pras duas
    # extensões; distinguir uma da outra exigiria abrir o ZIP e checar o
    # conteúdo interno, o que esta checagem não faz.
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    # OLE Compound File — formato binário legado do Office (doc/xls antigos).
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
}

_MAIOR_ASSINATURA = max(len(sig) for sigs in _ASSINATURAS_POR_EXTENSAO.values() for sig in sigs)


def validar_arquivo(arquivo) -> None:
    if arquivo.size > MAX_UPLOAD_SIZE_BYTES:
        limite_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise ValidationError(f"Arquivo maior que {limite_mb}MB.")

    extensao = os.path.splitext(arquivo.name)[1].lower()
    if extensao not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Extensão '{extensao}' não permitida.")

    assinaturas = _ASSINATURAS_POR_EXTENSAO.get(extensao)
    if assinaturas is not None:
        cabecalho = arquivo.read(_MAIOR_ASSINATURA)
        arquivo.seek(0)
        if not any(cabecalho.startswith(sig) for sig in assinaturas):
            raise ValidationError(
                f"O conteúdo do arquivo não corresponde a um '{extensao}' válido."
            )
