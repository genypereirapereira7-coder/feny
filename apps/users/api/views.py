from django.contrib.auth import authenticate
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.permissions import role_required
from apps.users import two_factor
from apps.users.api.serializers import UserAdminSerializer, UserSerializer
from apps.users.models import Role, User


class UserViewSet(viewsets.ModelViewSet):
    """`/api/v1/users/` — administração de contas. Só ADMIN.

    A ação `me` (própria identidade) é a única exceção: qualquer usuário
    autenticado pode consultar a si mesmo.
    """

    queryset = User.objects.all().order_by("username")
    serializer_class = UserAdminSerializer
    permission_classes = [role_required(Role.ADMIN)]

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)

    @action(detail=True, methods=["post"], url_path="reset-2fa")
    def reset_2fa(self, request: Request, pk=None) -> Response:
        """Único jeito de destravar alguém que perdeu o dispositivo — sem
        isto, 2FA obrigatório (§13) vira um jeito de trancar a própria conta
        pra sempre. Zera segredo e status; a pessoa configura de novo em
        `/auth/2fa/setup/` no próximo login."""
        user = self.get_object()
        user.two_factor_enabled = False
        user.two_factor_secret = ""
        user.save(update_fields=["two_factor_enabled", "two_factor_secret"])
        return Response(UserAdminSerializer(user).data)


def _emitir_tokens(user, *, requires_2fa_setup: bool) -> dict:
    refresh = RefreshToken.for_user(user)
    if requires_2fa_setup:
        # A claim vai no access E no refresh — um refresh feito com este
        # token continuaria restrito, então a pessoa é forçada a terminar o
        # cadastro de 2FA antes de conseguir qualquer sessão de verdade.
        refresh["requires_2fa_setup"] = True
        refresh.access_token["requires_2fa_setup"] = True
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "requires_2fa_setup": requires_2fa_setup,
    }


class LoginView(APIView):
    """`POST /api/v1/auth/token/` — substitui o `TokenObtainPairView` padrão
    do simplejwt pra encaixar 2FA (ARCHITECTURE.md §13) num único passo:
    quem tem 2FA ativo manda `otp_code` junto com usuário/senha na mesma
    chamada (mais simples pro cliente da API do que um desafio em duas
    etapas separadas)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request: Request) -> Response:
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = authenticate(request._request, username=username, password=password)

        if user is None or not user.is_active:
            return Response({"detail": "Credenciais inválidas."}, status=status.HTTP_401_UNAUTHORIZED)

        if user.two_factor_enabled:
            codigo = request.data.get("otp_code", "")
            if not two_factor.verificar_codigo(user.two_factor_secret, codigo):
                return Response(
                    {"detail": "Código de autenticação em duas etapas ausente ou inválido.", "requires_otp": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            return Response(_emitir_tokens(user, requires_2fa_setup=False))

        return Response(_emitir_tokens(user, requires_2fa_setup=two_factor.precisa_configurar_2fa(user)))


class TwoFactorSetupView(APIView):
    """`POST /api/v1/auth/2fa/setup/` — gera um novo segredo (substitui
    qualquer um anterior ainda não confirmado) e devolve o necessário pro
    frontend montar o QR code. Não ativa nada sozinho — só
    `TwoFactorConfirmView`, provando posse do segredo, faz isso."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        secret = two_factor.gerar_segredo()
        request.user.two_factor_secret = secret
        request.user.two_factor_enabled = False
        request.user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
        return Response({"secret": secret, "otpauth_url": two_factor.provisioning_uri(request.user, secret)})


class TwoFactorConfirmView(APIView):
    """`POST /api/v1/auth/2fa/confirm/` — só liga `two_factor_enabled` depois
    de um código válido provar que o segredo foi carregado com sucesso no
    app autenticador. Devolve um par de tokens novo, sem a claim restritiva,
    pra quem estava numa sessão de "só configuração" trocar na hora."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        codigo = request.data.get("code", "")
        if not two_factor.verificar_codigo(request.user.two_factor_secret, codigo):
            return Response({"detail": "Código inválido."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.two_factor_enabled = True
        request.user.save(update_fields=["two_factor_enabled"])
        return Response(_emitir_tokens(request.user, requires_2fa_setup=False))
