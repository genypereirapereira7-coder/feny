from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.choices import PaymentMethod
from apps.core.models import BaseModel
from apps.customers.validators import somente_digitos, validar_cnpj, validar_cpf


class CustomerKind(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", "Pessoa física"
    COMPANY = "COMPANY", "Pessoa jurídica"


class Customer(BaseModel):
    """Cliente/empresa da Feny (ARCHITECTURE.md §6.2 e §7 da spec de negócio).

    `created_by` não estava no modelo original do documento de arquitetura —
    foi adicionado aqui porque a matriz de permissões (§9) exige "vendedor
    edita só os próprios clientes", e isso não é implementável sem saber quem
    criou o quê. É o tipo de refinamento que a própria arquitetura antecipa
    (§: "a estrutura poderá ser modificada caso a análise demonstre
    necessidade").
    """

    kind = models.CharField(max_length=20, choices=CustomerKind.choices)
    legal_name = models.CharField(max_length=200)
    # Só dígitos, sempre — a formatação (pontos/traço) é problema de exibição
    # do frontend, não de armazenamento.
    document = models.CharField(max_length=14, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="customers_created", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "customers_customer"
        ordering = ["legal_name"]

    def clean(self):
        """Roda depois de `clean_fields()` — o documento já está normalizado
        (ver `save()`), então aqui só resta checar o dígito verificador."""
        if self.kind == CustomerKind.INDIVIDUAL and not validar_cpf(self.document):
            raise ValidationError({"document": "CPF inválido."})
        if self.kind == CustomerKind.COMPANY and not validar_cnpj(self.document):
            raise ValidationError({"document": "CNPJ inválido."})

    def save(self, *args, **kwargs):
        # Normalizar ANTES do `full_clean()`: `clean_fields()` valida
        # `max_length` no valor bruto, e "11.222.333/0001-81" tem 18
        # caracteres — falharia por tamanho antes de `clean()" ter a chance
        # de tirar a pontuação.
        self.document = somente_digitos(self.document)
        # Roda a validação mesmo fora da API (admin, shell, comando de
        # management) — a API valida de novo no serializer só pra devolver um
        # 400 arrumado em vez de deixar o ValidationError do model estourar.
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.legal_name


class CustomerContact(BaseModel):
    customer = models.ForeignKey(Customer, related_name="contacts", on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "customers_customercontact"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.customer.legal_name})"
