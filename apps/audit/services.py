"""Ponto único de escrita de auditoria. Services de domínio chamam `record`
explicitamente nos pontos críticos — não existe automação por signal aqui de
propósito (ver docstring de `AuditLog`)."""

from typing import Any

from apps.audit.models import AuditLog


def record(
    *,
    user,
    action: str,
    entity,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity._meta.label_lower,
        entity_id=str(entity.pk),
        before=before,
        after=after,
        metadata=metadata or {},
    )
