import os

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class DocumentCategory(models.TextChoices):
    CONTRACT = "CONTRACT", "Contrato"
    INVOICE = "INVOICE", "Nota fiscal"
    RECEIPT = "RECEIPT", "Comprovante"
    PROJECT_FILE = "PROJECT_FILE", "Arquivo de projeto"
    OTHER = "OTHER", "Outro"


def caminho_storage(instance: "Document", filename: str) -> str:
    """Caminho no storage — nunca o nome original do arquivo.

    Usar `instance.id` (já um UUID no momento da instanciação, ver
    `BaseModel`) em vez do nome enviado evita path traversal, caractere
    estranho no filesystem e colisão de nome — o nome original continua
    disponível em `original_filename`, só não é usado como caminho físico.
    """
    extensao = os.path.splitext(filename)[1].lower()
    return f"documents/{instance.id}{extensao}"


class Document(BaseModel):
    """Metadados de um arquivo (ARCHITECTURE.md §6.6 e §14).

    O binário não mora no Postgres — `file` é resolvido pelo backend de
    storage configurado (filesystem em dev, storage externo em produção); o
    banco guarda só a referência e os metadados.

    `project` fica de fora por enquanto — só entra na Fase 4, quando
    `apps.projects.Project` existir (ARCHITECTURE.md §6.6 já antecipa os
    dois relacionamentos; adicionar a FK antes da hora seria modelar em cima
    de um app que ainda não existe).
    """

    customer = models.ForeignKey(
        "customers.Customer", null=True, blank=True, related_name="documents",
        on_delete=models.SET_NULL,
    )
    category = models.CharField(max_length=20, choices=DocumentCategory.choices)
    file = models.FileField(upload_to=caminho_storage)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="documents_uploaded", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "documents_document"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.original_filename
