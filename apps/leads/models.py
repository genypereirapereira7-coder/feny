from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.choices import ProjectType
from apps.core.models import BaseModel
from apps.leads.validators import normalizar_telefone, telefone_valido, tem_letra


class LeadStatus(models.TextChoices):
    NEW = "NEW", "Novo"
    CONTACTED = "CONTACTED", "Em contato"
    QUALIFIED = "QUALIFIED", "Qualificado"
    CONVERTED = "CONVERTED", "Convertido"
    DISCARDED = "DISCARDED", "Descartado"


class BudgetRange(models.TextChoices):
    """Faixa, nunca valor exato: ninguém digita orçamento real num formulário
    de primeiro contato, e pedir isso derruba conversão. Serve só pra ordenar
    a fila de atendimento — o número de verdade nasce no orçamento (§6.3)."""

    UNDECIDED = "UNDECIDED", "Ainda não sei"
    UNDER_5K = "UNDER_5K", "Até R$ 5 mil"
    FROM_5K_TO_15K = "FROM_5K_TO_15K", "R$ 5 mil a R$ 15 mil"
    FROM_15K_TO_40K = "FROM_15K_TO_40K", "R$ 15 mil a R$ 40 mil"
    ABOVE_40K = "ABOVE_40K", "Acima de R$ 40 mil"


class Lead(BaseModel):
    """Contato que chegou pelo site público, antes de ser cliente.

    Domínio novo — não existia em nenhuma das 10 fases originais, nasceu junto
    com o site institucional. Fica separado de `customers.Customer` de
    propósito: um lead não tem CPF/CNPJ, não tem forma de pagamento preferida
    e a maioria nunca vira cliente. Misturar os dois encheria a base de
    clientes de gente que só mandou uma mensagem, e obrigaria `document` a
    virar opcional — justo o campo que hoje é a chave única de cliente.

    A ponte entre os dois é `customer`: quando o lead fecha negócio, alguém
    cadastra o cliente de verdade (com documento validado) e marca a conversão
    por `services.converter_em_cliente`.
    """

    # --- o que o visitante preenche ---
    name = models.CharField(max_length=150)
    company = models.CharField(max_length=150, blank=True)
    email = models.EmailField()
    # Só dígitos, sem +55 — mesma disciplina de `Customer.document`.
    phone = models.CharField(max_length=11)
    service_type = models.CharField(max_length=20, choices=ProjectType.choices)
    budget_range = models.CharField(
        max_length=20, choices=BudgetRange.choices, default=BudgetRange.UNDECIDED,
    )
    message = models.TextField()

    # --- o que a Feny preenche depois ---
    status = models.CharField(
        max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW, db_index=True,
    )
    internal_notes = models.TextField(blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, related_name="leads_handled", on_delete=models.SET_NULL,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        null=True, blank=True, related_name="leads", on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "leads_lead"
        ordering = ["-created_at"]
        indexes = [
            # A tela de Leads abre filtrando por status e ordenada por data;
            # sem o índice composto o Postgres varre a tabela inteira assim
            # que o volume passar de alguns milhares (Fase 10, §13).
            models.Index(fields=["status", "-created_at"], name="leads_status_created_idx"),
        ]

    def clean(self):
        """Roda depois de `clean_fields()`, com o telefone já normalizado
        (ver `save()`) — aqui só resta o que `max_length`/`EmailField` não
        pegam sozinhos."""
        erros = {}

        if not tem_letra(self.name) or len(self.name.strip()) < 2:
            erros["name"] = "Informe seu nome."
        if not telefone_valido(self.phone):
            erros["phone"] = "Telefone inválido — informe DDD + número."
        if len(self.message.strip()) < 10:
            erros["message"] = "Conte um pouco mais sobre o que você precisa (mínimo 10 caracteres)."
        if self.status == LeadStatus.CONVERTED and self.customer_id is None:
            erros["customer"] = "Um lead convertido precisa apontar para o cliente cadastrado."

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        # Normalizar ANTES do `full_clean()`: `clean_fields()` checa o
        # `max_length=11` no valor bruto, e "(71) 99999-8888" tem 15
        # caracteres — falharia por tamanho antes de `clean()` ter a chance de
        # tirar a pontuação.
        self.phone = normalizar_telefone(self.phone)
        self.name = self.name.strip()
        self.company = self.company.strip()
        self.email = self.email.strip().lower()
        self.message = self.message.strip()
        # Valida mesmo fora da API (admin, shell, comando de management) —
        # mesmo padrão de `Customer.save()`.
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} — {self.get_status_display()}"


class ClientePotencial(BaseModel):
    """Negócio fechado pelo agente de IA no WhatsApp (Typebot + Evolution API).

    Chega por `views.webhook_whatsapp_ia` quando a conversa atinge a palavra
    `[FECHADO]`: o robô já conversou, entendeu o projeto e estimou um valor.
    É um estágio adiante do `Lead` acima, que é o contato cru do formulário do
    site — por isso os campos são outros (aqui já existe descrição de projeto
    e valor; lá existe faixa de orçamento e mensagem solta).

    O telefone é a chave única de verdade: no WhatsApp é ele que identifica a
    pessoa, e a mesma conversa reenviada pelo Typebot (retentativa, clique
    duplo no fluxo) não pode virar dois registros. Guardado só em dígitos e
    sem o +55, mesma disciplina de `Lead.phone` e `Customer.document`.
    """

    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=11, unique=True)
    descricao_projeto = models.TextField()

    # `null=True` de propósito, e é a única liberdade que este modelo toma em
    # relação ao pedido: fechamento sem valor declarado continua sendo
    # fechamento. Exigir o número faria o webhook recusar a conversa inteira
    # quando o robô não conseguisse extrair o valor — trocar um dado que falta
    # por todos os outros que já vieram.
    valor_estimado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        verbose_name = "cliente potencial"
        verbose_name_plural = "clientes potenciais"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.nome} ({self.telefone})"

    @property
    def data_cadastro(self):
        """Apelido de leitura pro `created_at` que vem do `BaseModel`.

        O nome pedido na especificação é este; a coluna não é criada duas
        vezes porque duas datas de cadastro no mesmo registro são duas coisas
        que podem discordar — e a que o resto da plataforma lê é `created_at`.
        """
        return self.created_at
