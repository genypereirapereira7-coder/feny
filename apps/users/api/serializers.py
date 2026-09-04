from rest_framework import serializers

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Leitura de usuário — usada em `/users/` e `/users/me/`.

    Campos administrativos (`role`, `is_active`, `is_staff`) são somente
    leitura aqui: mudar o próprio papel não é uma operação que o usuário faz
    sobre si mesmo (ARCHITECTURE.md §12 — nenhum campo crítico livre pro
    cliente da API). A escrita desses campos fica para o `UserAdminSerializer`,
    restrito a quem tem permissão de administrar usuários.
    """

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "role", "is_active", "two_factor_enabled", "date_joined", "last_login",
        )
        read_only_fields = fields


class UserAdminSerializer(serializers.ModelSerializer):
    """CRUD de usuário para quem administra contas (ADMIN).

    `two_factor_enabled` é leitura — a única forma de ligar é confirmar um
    código de verdade em `TwoFactorConfirmView`, e a única forma de desligar
    é `UserViewSet.reset_2fa`. Deixar isto editável aqui permitiria ativar
    2FA pra alguém sem nenhum segredo configurado (trancando a conta) ou
    desativar silenciosamente por um PATCH qualquer (ARCHITECTURE.md §12:
    campo crítico nunca livre pro cliente da API)."""

    password = serializers.CharField(write_only=True, required=False, min_length=10)

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "role", "is_active", "two_factor_enabled", "password",
        )
        read_only_fields = ("two_factor_enabled",)

    def create(self, validated_data):
        senha = validated_data.pop("password", None)
        usuario = User(**validated_data)
        if senha:
            usuario.set_password(senha)
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        senha = validated_data.pop("password", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if senha:
            instance.set_password(senha)
        instance.save()
        return instance
