from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.exceptions import DomainError
from apps.customers.models import Customer
from apps.leads import services
from apps.leads.api.serializers import LeadSerializer, PublicLeadSerializer
from apps.leads.models import Lead
from apps.leads.permissions import LeadPermission

# Duas mensagens iguais do mesmo e-mail dentro desta janela são o mesmo
# contato — clique duplo, F5 no envio, conexão ruim. O segundo envio responde
# "recebido" e não cria lead nenhum, em vez de encher a fila de duplicata.
JANELA_ENVIO_DUPLICADO = timedelta(minutes=10)

# Resposta única do endpoint público, dê no que der: e-mail repetido, robô
# pego na armadilha ou lead criado de verdade. Quem manda o formulário não
# tem o que fazer com a diferença, e um atacante não usa a resposta pra
# descobrir se um e-mail já está na base.
RECEBIDO = {"detail": "Recebemos seu contato. A Feny responde em até 1 dia útil."}


class PublicLeadCreateView(CreateAPIView):
    """`POST /api/v1/public/contact/` — formulário do site institucional.

    Único ponto da API sem autenticação. Três travas, porque uma só não
    resolve: `AllowAny` + throttle por IP (volume), armadilha `website`
    (robô), e janela de duplicata (dedo nervoso). Nunca devolve o lead criado
    — só a confirmação; o site não tem nada a fazer com o registro.
    """

    serializer_class = PublicLeadSerializer
    permission_classes = [AllowAny]
    # Sem autenticação nenhuma na view, e não é só redundância com o
    # `AllowAny`: o `SessionAuthentication` do padrão global aplica CSRF
    # quando encontra sessão válida, então um visitante que por acaso esteja
    # logado no /admin no mesmo navegador levaria 403 ao mandar o formulário.
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "lead-public"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        # A armadilha não vira erro de validação de propósito: devolver 400
        # ensinaria o robô qual campo deixar em branco na próxima tentativa.
        caiu_na_armadilha = bool(dados.pop("website", "").strip())
        if caiu_na_armadilha:
            return Response(RECEBIDO, status=status.HTTP_201_CREATED)

        duplicado = Lead.objects.filter(
            email=dados["email"].strip().lower(),
            message=dados["message"],
            created_at__gte=timezone.now() - JANELA_ENVIO_DUPLICADO,
        ).exists()
        if not duplicado:
            serializer.save()

        return Response(RECEBIDO, status=status.HTTP_201_CREATED)


class LeadViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Tela de Leads do painel. Sem `create` (lead nasce no site, não na mão)
    e sem `destroy` (lead ruim vira `DISCARDED`, e o histórico fica)."""

    queryset = Lead.objects.select_related("handled_by", "customer")
    serializer_class = LeadSerializer
    permission_classes = [LeadPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "company", "email", "phone", "message"]
    ordering_fields = ["created_at", "name", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        situacao = self.request.query_params.get("status")
        if situacao:
            qs = qs.filter(status=situacao)
        return qs

    @action(detail=True, methods=["post"], url_path="contatar")
    def contatar(self, request, pk=None):
        lead = services.marcar_em_contato(self.get_object(), request.user)
        return Response(self.get_serializer(lead).data)

    @action(detail=True, methods=["post"], url_path="qualificar")
    def qualificar(self, request, pk=None):
        lead = services.qualificar(self.get_object(), request.user)
        return Response(self.get_serializer(lead).data)

    @action(detail=True, methods=["post"], url_path="converter")
    def converter(self, request, pk=None):
        customer_id = request.data.get("customer")
        if not customer_id:
            raise DomainError("Escolha o cliente já cadastrado que este lead virou.")
        customer = get_object_or_404(Customer, pk=customer_id)
        lead = services.converter_em_cliente(self.get_object(), request.user, customer)
        return Response(self.get_serializer(lead).data)

    @action(detail=True, methods=["post"], url_path="descartar")
    def descartar(self, request, pk=None):
        lead = services.descartar(self.get_object(), request.user, request.data.get("motivo", ""))
        return Response(self.get_serializer(lead).data)

    @action(detail=True, methods=["post"], url_path="reabrir")
    def reabrir(self, request, pk=None):
        lead = services.reabrir(self.get_object(), request.user)
        return Response(self.get_serializer(lead).data)
