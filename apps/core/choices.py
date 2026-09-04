"""Enums compartilhados por mais de um domínio — evita redefinir o mesmo
`TextChoices` em dois apps (ARCHITECTURE.md §21: uma regra, uma fonte)."""

from django.db import models


class PaymentMethod(models.TextChoices):
    BOLETO = "BOLETO", "Boleto"
    CARD = "CARD", "Cartão"


class ProjectType(models.TextChoices):
    """Vive aqui e não em `apps.projects` (que só nasce na Fase 4) porque
    `quotations.service_type` já precisa dela na Fase 3 — ARCHITECTURE.md §6.3
    referencia os mesmos tipos definidos em §6.4."""

    SYSTEM = "SYSTEM", "Sistema"
    AUTOMATION = "AUTOMATION", "Automação"
    WEBSITE = "WEBSITE", "Site"
    PWA = "PWA", "PWA"
    APP = "APP", "Aplicativo"
    SAAS = "SAAS", "SaaS"
    OTHER = "OTHER", "Outro"
