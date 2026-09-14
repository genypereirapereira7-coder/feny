from rest_framework import serializers

from apps.leads.models import Lead
from apps.leads.validators import normalizar_telefone, telefone_valido, tem_letra


class PublicLeadSerializer(serializers.ModelSerializer):
    """Entrada do formulário do site — aberto pra internet, sem autenticação.

    Lista os campos de escrita um a um (nada de `__all__`): `status`,
    `handled_by`, `internal_notes` e `customer` existem no model e um visitante
    não pode encostar em nenhum deles. Se um dia alguém adicionar um campo
    sensível no model, ele não vaza pra cá por esquecimento.
    """

    # Aceita o valor ainda formatado ("(71) 99999-8888") — o `max_length=11`
    # do model é sobre o telefone já normalizado, então validar o bruto por
    # tamanho rejeitaria entrada correta (mesmo motivo do `document` em
    # `customers.api.serializers`).
    phone = serializers.CharField(max_length=24)
    # Armadilha pra robô de formulário: campo escondido por CSS, invisível
    # pra gente de verdade. Bot que preenche tudo que encontra cai aqui. Não é
    # o `throttle` — aquele limita volume, este separa humano de script.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Lead
        fields = ("name", "company", "email", "phone", "service_type", "budget_range", "message", "website")

    def validate_name(self, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 2 or not tem_letra(valor):
            raise serializers.ValidationError("Informe seu nome.")
        return valor

    def validate_phone(self, valor: str) -> str:
        if not telefone_valido(valor):
            raise serializers.ValidationError("Telefone inválido — informe DDD + número.")
        return normalizar_telefone(valor)

    def validate_message(self, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < 10:
            raise serializers.ValidationError("Conte um pouco mais sobre o que você precisa (mínimo 10 caracteres).")
        if len(valor) > 2000:
            raise serializers.ValidationError("Mensagem muito longa — resuma em até 2000 caracteres.")
        return valor

    def validate_company(self, valor: str) -> str:
        return valor.strip()


class LeadSerializer(serializers.ModelSerializer):
    """Leitura interna (tela de Leads do painel).

    Quase tudo é somente-leitura: `status` e `customer` só mudam por ação de
    domínio em `apps/leads/services.py`, nunca por PATCH direto — a mesma
    disciplina de orçamento, projeto e chamado. O que sobra pra editar à mão
    é anotação interna e a quem o lead pertence.
    """

    handled_by_name = serializers.CharField(source="handled_by.first_name", read_only=True, default="")
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True, default="")
    service_type_display = serializers.CharField(source="get_service_type_display", read_only=True)
    budget_range_display = serializers.CharField(source="get_budget_range_display", read_only=True)

    class Meta:
        model = Lead
        fields = (
            "id", "name", "company", "email", "phone", "service_type", "service_type_display",
            "budget_range", "budget_range_display", "message", "status", "internal_notes",
            "handled_by", "handled_by_name", "customer", "customer_name",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "name", "company", "email", "phone", "service_type", "budget_range",
            "message", "status", "customer", "created_at", "updated_at",
        )
