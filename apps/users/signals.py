"""Mantém `user.groups` sincronizado com `user.role`.

O Group é a unidade que carrega as `Permission` de cada domínio (adicionadas
conforme cada app de negócio é construído nas próximas fases). Sem este
signal, mudar o `role` de alguém pela API/admin não moveria a pessoa entre os
grupos, e a permissão ficaria desalinhada do cargo mostrado na tela.
"""

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import Role, User


@receiver(post_save, sender=User)
def sincronizar_grupo_do_papel(sender, instance: User, **kwargs) -> None:
    """Tira o usuário de qualquer grupo-de-papel antigo e põe no do `role` atual.

    Só mexe nos grupos cujo nome é um `Role` — um grupo customizado que não
    representa cargo (se algum dia existir) não é tocado por aqui.
    """
    grupos_de_papel = Group.objects.filter(name__in=Role.values)
    instance.groups.remove(*grupos_de_papel)

    if instance.role:
        grupo, _ = Group.objects.get_or_create(name=instance.role)
        instance.groups.add(grupo)
