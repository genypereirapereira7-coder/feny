"""Autenticação JWT com uma trava extra (ARCHITECTURE.md §13): um token
emitido pra um usuário de papel com 2FA obrigatório que ainda não configurou
carrega `requires_2fa_setup` — e só abre as rotas de configuração, todo o
resto fica bloqueado até a confirmação (`TwoFactorConfirmView`). Ver
`apps/users/two_factor.py` e `apps/users/api/views.py::LoginView`.

Trocar isto no `DEFAULT_AUTHENTICATION_CLASSES` (em vez de uma permission
class por view) é deliberado: nenhum ViewSet do projeto precisa saber que
essa trava existe, e nenhum vai esquecer de aplicá-la — autenticação roda
antes de qualquer `permission_classes` específico, pra toda view.
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

ROTAS_PERMITIDAS_SEM_2FA_CONFIGURADO = (
    "/api/v1/users/me/",
    "/api/v1/auth/2fa/setup/",
    "/api/v1/auth/2fa/confirm/",
    "/api/v1/auth/token/refresh/",
)


class TwoFactorAwareJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado is None:
            return None

        user, validated_token = resultado
        if validated_token.get("requires_2fa_setup") and request.path not in ROTAS_PERMITIDAS_SEM_2FA_CONFIGURADO:
            raise AuthenticationFailed(
                "Configure a autenticação em duas etapas antes de continuar (POST /api/v1/auth/2fa/setup/)."
            )
        return user, validated_token
