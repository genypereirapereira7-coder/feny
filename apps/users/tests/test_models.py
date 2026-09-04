from django.contrib.auth.models import Group
from django.test import TestCase

from apps.users.models import Role, User


class UserRoleGroupSyncTests(TestCase):
    """O signal em `apps/users/signals.py` deve manter os grupos alinhados ao role."""

    def test_criar_usuario_entra_no_grupo_do_papel(self):
        usuario = User.objects.create_user(username="vendedor1", password="senha-forte-123", role=Role.SALES)

        self.assertTrue(usuario.groups.filter(name=Role.SALES).exists())
        self.assertEqual(usuario.groups.count(), 1)

    def test_trocar_papel_move_o_usuario_de_grupo(self):
        usuario = User.objects.create_user(username="funcionario1", password="senha-forte-123", role=Role.SALES)

        usuario.role = Role.FINANCE
        usuario.save()

        self.assertFalse(usuario.groups.filter(name=Role.SALES).exists())
        self.assertTrue(usuario.groups.filter(name=Role.FINANCE).exists())

    def test_nao_mexe_em_grupo_que_nao_representa_papel(self):
        grupo_extra = Group.objects.create(name="Time Noturno")
        usuario = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)
        usuario.groups.add(grupo_extra)

        usuario.role = Role.MANAGER
        usuario.save()

        self.assertTrue(usuario.groups.filter(name="Time Noturno").exists())
        self.assertTrue(usuario.groups.filter(name=Role.MANAGER).exists())
        self.assertFalse(usuario.groups.filter(name=Role.DEVELOPER).exists())
