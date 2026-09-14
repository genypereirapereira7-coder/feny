from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.choices import PaymentMethod, ProjectType
from apps.customers.models import Customer, CustomerKind
from apps.leads.models import BudgetRange, Lead, LeadStatus
from apps.users.models import Role, User

FORMULARIO_VALIDO = {
    "name": "Maria Souza",
    "company": "Padaria Pão Quente",
    "email": "Maria@Exemplo.com",
    "phone": "(71) 99999-8888",
    "service_type": ProjectType.SYSTEM,
    "budget_range": BudgetRange.FROM_5K_TO_15K,
    "message": "Preciso de um sistema pra controlar os pedidos da padaria.",
}


def _formulario(**mudancas):
    return {**FORMULARIO_VALIDO, **mudancas}


class FormularioPublicoTests(APITestCase):
    """O endpoint aberto pra internet — nenhum destes testes autentica nada."""

    url = "/api/v1/public/contact/"

    def setUp(self):
        # O throttle guarda a contagem por IP no cache, que é do processo
        # inteiro e não volta atrás no fim de cada teste como o banco. Sem
        # limpar, o 6º POST da suíte levaria 429 e derrubaria testes que não
        # têm nada a ver com limite de envio.
        cache.clear()

    def test_visitante_anonimo_envia_contato(self):
        resposta = self.client.post(self.url, _formulario())

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        lead = Lead.objects.get()
        self.assertEqual(lead.status, LeadStatus.NEW)
        # Normalizado no caminho: telefone só com dígitos, e-mail em minúscula.
        self.assertEqual(lead.phone, "71999998888")
        self.assertEqual(lead.email, "maria@exemplo.com")

    def test_resposta_nao_devolve_o_lead(self):
        """Confirmação e nada mais — o site não tem o que fazer com o registro,
        e devolver id/status daria a um robô um jeito de sondar a base."""
        resposta = self.client.post(self.url, _formulario())
        self.assertEqual(list(resposta.data.keys()), ["detail"])

    def test_visitante_nao_escolhe_o_status_do_proprio_lead(self):
        self.client.post(self.url, _formulario(status=LeadStatus.QUALIFIED, internal_notes="me atende primeiro"))

        lead = Lead.objects.get()
        self.assertEqual(lead.status, LeadStatus.NEW)
        self.assertEqual(lead.internal_notes, "")

    def test_telefone_invalido_e_recusado(self):
        for telefone in ("", "123", "0000000000", "(71) 12345-6789", "71 3333-333"):
            with self.subTest(telefone=telefone):
                resposta = self.client.post(self.url, _formulario(phone=telefone))
                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("phone", resposta.data)
        self.assertEqual(Lead.objects.count(), 0)

    def test_telefone_com_codigo_do_pais_e_aceito(self):
        resposta = self.client.post(self.url, _formulario(phone="+55 (71) 99999-8888"))

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lead.objects.get().phone, "71999998888")

    def test_fixo_de_oito_digitos_e_aceito(self):
        resposta = self.client.post(self.url, _formulario(phone="(71) 3333-4444"))
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)

    def test_campos_de_texto_precisam_de_conteudo_de_verdade(self):
        casos = [("name", "   "), ("name", "123"), ("message", "oi"), ("message", "    ")]
        for campo, valor in casos:
            with self.subTest(campo=campo, valor=valor):
                resposta = self.client.post(self.url, _formulario(**{campo: valor}))
                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(campo, resposta.data)

    def test_email_invalido_e_recusado(self):
        resposta = self.client.post(self.url, _formulario(email="maria@"))
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", resposta.data)

    def test_tipo_de_servico_fora_da_lista_e_recusado(self):
        resposta = self.client.post(self.url, _formulario(service_type="FOGUETE"))
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_armadilha_de_robo_responde_igual_mas_nao_salva(self):
        resposta = self.client.post(self.url, _formulario(website="http://spam.example"))

        # Mesma resposta de um envio bom — de propósito: um 400 aqui ensinaria
        # o robô qual campo deixar em branco na próxima tentativa.
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lead.objects.count(), 0)

    def test_envio_repetido_nao_duplica_o_lead(self):
        self.client.post(self.url, _formulario())
        resposta = self.client.post(self.url, _formulario())

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lead.objects.count(), 1)

    def test_excesso_de_envios_e_barrado(self):
        """5/min por IP — o teto que separa "errei um campo e reenviei" de spam."""
        for numero in range(5):
            resposta = self.client.post(self.url, _formulario(message=f"Mensagem número {numero} do site."))
            self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)

        barrado = self.client.post(self.url, _formulario(message="Mais uma mensagem de teste."))
        self.assertEqual(barrado.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(Lead.objects.count(), 5)

    def test_mesma_pessoa_volta_depois_da_janela_e_vira_lead_novo(self):
        self.client.post(self.url, _formulario())
        antigo = Lead.objects.get()
        Lead.objects.filter(pk=antigo.pk).update(created_at=timezone.now() - timedelta(hours=2))

        self.client.post(self.url, _formulario())
        self.assertEqual(Lead.objects.count(), 2)


class LeadPainelTests(APITestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.gerente = User.objects.create_user(username="g1", password="senha-forte-123", role=Role.MANAGER)
        self.suporte = User.objects.create_user(username="s1", password="senha-forte-123", role=Role.SUPPORT)
        self.financeiro = User.objects.create_user(username="f1", password="senha-forte-123", role=Role.FINANCE)
        self.lead = Lead.objects.create(
            name="Maria Souza", email="maria@exemplo.com", phone="71999998888",
            service_type=ProjectType.SYSTEM, message="Preciso de um sistema pra padaria.",
        )

    def test_financeiro_nao_ve_leads(self):
        self.client.force_authenticate(self.financeiro)
        self.assertEqual(self.client.get("/api/v1/leads/").status_code, status.HTTP_403_FORBIDDEN)

    def test_suporte_ve_mas_nao_atende(self):
        self.client.force_authenticate(self.suporte)
        self.assertEqual(self.client.get("/api/v1/leads/").status_code, status.HTTP_200_OK)
        resposta = self.client.post(f"/api/v1/leads/{self.lead.id}/contatar/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonimo_nao_lista_leads(self):
        self.assertEqual(self.client.get("/api/v1/leads/").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_fluxo_do_atendimento(self):
        self.client.force_authenticate(self.vendedor)

        contato = self.client.post(f"/api/v1/leads/{self.lead.id}/contatar/")
        self.assertEqual(contato.data["status"], LeadStatus.CONTACTED)
        # Quem tocou primeiro fica como responsável, sem ninguém precisar atribuir.
        self.assertEqual(contato.data["handled_by"], self.vendedor.id)

        qualificado = self.client.post(f"/api/v1/leads/{self.lead.id}/qualificar/")
        self.assertEqual(qualificado.data["status"], LeadStatus.QUALIFIED)

    def test_nao_pula_etapa(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.post(f"/api/v1/leads/{self.lead.id}/qualificar/")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, LeadStatus.NEW)

    def test_conversao_exige_cliente_cadastrado(self):
        self.client.force_authenticate(self.gerente)
        self.client.post(f"/api/v1/leads/{self.lead.id}/contatar/")

        sem_cliente = self.client.post(f"/api/v1/leads/{self.lead.id}/converter/", {})
        self.assertEqual(sem_cliente.status_code, status.HTTP_400_BAD_REQUEST)

        cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Maria Souza", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.gerente,
        )
        convertido = self.client.post(
            f"/api/v1/leads/{self.lead.id}/converter/", {"customer": str(cliente.id)},
        )
        self.assertEqual(convertido.data["status"], LeadStatus.CONVERTED)
        self.assertEqual(convertido.data["customer_name"], "Maria Souza")

    def test_descarte_exige_motivo_e_guarda_na_anotacao(self):
        self.client.force_authenticate(self.vendedor)

        sem_motivo = self.client.post(f"/api/v1/leads/{self.lead.id}/descartar/", {"motivo": "  "})
        self.assertEqual(sem_motivo.status_code, status.HTTP_400_BAD_REQUEST)

        descartado = self.client.post(
            f"/api/v1/leads/{self.lead.id}/descartar/", {"motivo": "Orçamento fora da faixa"},
        )
        self.assertEqual(descartado.data["status"], LeadStatus.DISCARDED)
        self.assertIn("Orçamento fora da faixa", descartado.data["internal_notes"])

        reaberto = self.client.post(f"/api/v1/leads/{self.lead.id}/reabrir/")
        self.assertEqual(reaberto.data["status"], LeadStatus.NEW)

    def test_status_nao_muda_por_patch_direto(self):
        """Transição é ação de domínio auditada — PATCH só edita anotação."""
        self.client.force_authenticate(self.gerente)
        resposta = self.client.patch(
            f"/api/v1/leads/{self.lead.id}/",
            {"status": LeadStatus.CONVERTED, "internal_notes": "Ligar amanhã"},
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["status"], LeadStatus.NEW)
        self.assertEqual(resposta.data["internal_notes"], "Ligar amanhã")

    def test_api_nao_cria_nem_exclui_lead(self):
        self.client.force_authenticate(self.gerente)
        criacao = self.client.post("/api/v1/leads/", {"name": "Fulano"})
        exclusao = self.client.delete(f"/api/v1/leads/{self.lead.id}/")

        self.assertEqual(criacao.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(exclusao.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filtra_por_status_e_busca(self):
        self.client.force_authenticate(self.vendedor)
        Lead.objects.create(
            name="João Lima", email="joao@exemplo.com", phone="7133334444",
            service_type=ProjectType.WEBSITE, message="Quero um site pra minha loja.",
        )
        self.client.post(f"/api/v1/leads/{self.lead.id}/contatar/")

        novos = self.client.get("/api/v1/leads/?status=NEW")
        self.assertEqual([lead["name"] for lead in novos.data["results"]], ["João Lima"])

        busca = self.client.get("/api/v1/leads/?search=padaria")
        self.assertEqual([lead["name"] for lead in busca.data["results"]], ["Maria Souza"])
