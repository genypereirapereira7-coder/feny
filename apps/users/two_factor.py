"""TOTP (2FA). Toda a lógica de segredo/código mora aqui, num lugar só — nem
a view nem o `authentication.py` calculam nada de TOTP diretamente.

2FA obrigatório por papel desligado a pedido do dono do sistema (queria
acesso direto, sem passo extra, sendo o único usuário real por enquanto).
O mecanismo continua funcionando pra quem configurar por conta própria via
`/auth/2fa/setup/` — só não é mais forçado em ninguém. Pra reativar a
obrigatoriedade: `PAPEIS_COM_2FA_OBRIGATORIO = (Role.ADMIN, Role.MANAGER,
Role.FINANCE)`.
"""

import pyotp

PAPEIS_COM_2FA_OBRIGATORIO = ()


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
