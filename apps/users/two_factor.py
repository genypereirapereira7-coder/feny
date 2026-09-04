"""TOTP (2FA) — ARCHITECTURE.md §13: "2FA obrigatório para role in (ADMIN,
MANAGER, FINANCE)". Toda a lógica de segredo/código mora aqui, num lugar só
— nem a view nem o `authentication.py` calculam nada de TOTP diretamente.
"""

import pyotp

from apps.users.models import Role

PAPEIS_COM_2FA_OBRIGATORIO = (Role.ADMIN, Role.MANAGER, Role.FINANCE)


def precisa_configurar_2fa(user) -> bool:
    return user.role in PAPEIS_COM_2FA_OBRIGATORIO and not user.two_factor_enabled


def gerar_segredo() -> str:
    return pyotp.random_base32()


def provisioning_uri(user, secret: str) -> str:
    """URL padrão `otpauth://` — qualquer app autenticador (Google
    Authenticator, Authy...) lê isso direto de um QR code gerado no frontend
    a partir desta string; gerar a imagem do QR não é responsabilidade do
    backend."""
    return pyotp.TOTP(secret).provisioning_uri(name=user.username, issuer_name="Feny")


def verificar_codigo(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)
