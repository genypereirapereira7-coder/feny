from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.documents.api.serializers import DocumentSerializer
from apps.documents.models import Document


class DocumentViewSet(viewsets.ModelViewSet):
    """Permissão por papel ainda não é fina aqui — a spec de negócio não
    define, por domínio, quem vê qual documento além de "controle de acesso"
    genérico (ARCHITECTURE.md §25). Fica IsAuthenticated até um caso de uso
    concreto pedir mais."""

    queryset = Document.objects.select_related("customer", "project", "uploaded_by")
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs
