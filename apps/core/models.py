import uuid

from django.db import models


class BaseModel(models.Model):
    """Base para as entidades de domínio — ver ARCHITECTURE.md §6.

    UUID como chave primária (não vaza sequência incremental, não colide entre
    ambientes) e timestamps sempre presentes. Toda entidade de domínio que
    cruza fronteira de API ou integração externa herda daqui.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
