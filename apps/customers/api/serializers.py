from rest_framework import serializers

from apps.customers.models import Customer, CustomerContact, CustomerKind
from apps.customers.validators import somente_digitos, validar_cnpj, validar_cpf


class CustomerContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerContact
        fields = ("id", "customer", "name", "role", "email", "phone", "created_at")
        read_only_fields = ("id", "created_at")


class CustomerSerializer(serializers.ModelSerializer):
    contacts = CustomerContactSerializer(many=True, read_only=True)
    # Campo declarado explicitamente (não deixado para o ModelSerializer
    # gerar sozinho) por dois motivos: o `max_length=14` do model é sobre o
    # valor já normalizado (só dígitos) — um CNPJ formatado de entrada
    # ("11.222.333/0001-81", 18 caracteres) seria rejeitado por tamanho antes
    # mesmo de `validate()` tirar a pontuação; e o `UniqueValidator`
    # automático do DRF roda sobre esse mesmo valor bruto, então nunca
    # detecta duplicata de verdade (ver `validate()` abaixo).
    document = serializers.CharField(max_length=32)

    class Meta:
        model = Customer
        fields = (
            "id", "kind", "legal_name", "document", "email", "phone",
            "preferred_payment_method", "created_by", "contacts",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def validate(self, attrs):
        """CPF/CNPJ de verdade, não só formato — ver `apps/customers/validators.py`.

        Duplica a checagem que `Customer.clean()` também faz porque aqui dá
        pra devolver um 400 da API com a mensagem certa; deixar o
        `ValidationError` do Django estourar de dentro do `.save()` viraria um
        500 feio.

        A checagem de unicidade também precisa ser manual, e não confiada ao
        `UniqueValidator` automático do DRF: ele roda campo a campo, antes
        deste método, sobre o valor *bruto* ainda com pontuação — então nunca
        bate com o valor já normalizado (só dígitos) salvo no banco, e deixa
        passar um duplicado que só estoura como `ValidationError` do Django
        (500) dentro de `full_clean()` no `.save()`.
        """
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        documento = somente_digitos(attrs.get("document", getattr(self.instance, "document", "")))
        attrs["document"] = documento

        if kind == CustomerKind.INDIVIDUAL and not validar_cpf(documento):
            raise serializers.ValidationError({"document": "CPF inválido."})
        if kind == CustomerKind.COMPANY and not validar_cnpj(documento):
            raise serializers.ValidationError({"document": "CNPJ inválido."})

        ja_existe = Customer.objects.filter(document=documento)
        if self.instance is not None:
            ja_existe = ja_existe.exclude(pk=self.instance.pk)
        if ja_existe.exists():
            raise serializers.ValidationError({"document": "Já existe um cliente com este documento."})

        return attrs
