"""Webhook do agente de IA do WhatsApp (`POST /api/v1/webhook-ia/`).

A segunda porta da plataforma aberta pra internet inteira. O que está testado
aqui é o que impede ela de virar um formulário de cadastro anônimo: o segredo
no cabeçalho, o telefone válido e a mesma conversa não virar dois registros.
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.leads.models import ClientePotencial

TOKEN = "segredo-de-teste"


@override_settings(WHATSAPP_IA_WEBHOOK_TOKEN=TOKEN)
class WebhookWhatsAppIaTests(TestCase):
    def setUp(self):
        self.url = reverse("webhook-whatsapp-ia")

    def postar(self, corpo, token=TOKEN, **extra):
        cabecalhos = {"HTTP_X_WEBHOOK_TOKEN": token} if token is not None else {}
        return self.client.post(
            self.url, data=corpo, content_type="application/json", **cabecalhos, **extra
        )

    # --- quem está batendo ---

    def test_get_nao_e_aceito(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_sem_token_recusa(self):
        resposta = self.postar({"texto": "[FECHADO]"}, token=None)
        self.assertEqual(resposta.status_code, 401)
        self.assertFalse(ClientePotencial.objects.exists())

    def test_token_errado_recusa(self):
        resposta = self.postar({"texto": "[FECHADO]"}, token="chute")
        self.assertEqual(resposta.status_code, 401)
        self.assertFalse(ClientePotencial.objects.exists())

    @override_settings(WHATSAPP_IA_WEBHOOK_TOKEN="")
    def test_sem_segredo_configurado_recusa_tudo(self):
        """Falha fechado: deploy sem a variável fica sem integração, não sem
        tranca. O contrário deixaria o endereço aberto pra qualquer um."""
        resposta = self.postar({"texto": "[FECHADO]"}, token="qualquer-coisa")
        self.assertEqual(resposta.status_code, 401)

    # --- o que veio ---

    def test_conversa_sem_fechamento_nao_salva(self):
        """E responde 200: não é erro. Devolvendo erro, o Typebot reenviaria a
        mesma mensagem em laço até desistir."""
        resposta = self.postar({"texto": "oi, quero um sistema", "telefone": "69992264398"})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.json()["salvo"])
        self.assertFalse(ClientePotencial.objects.exists())

    def test_fechamento_cadastra(self):
        resposta = self.postar({
            "texto": "Resumo da conversa [FECHADO]",
            "nome": "Maria Souza",
            "telefone": "(69) 99226-4398",
            "descricao_projeto": "Sistema de pedidos pra sorveteria",
            "valor_estimado": "12500.00",
        })

        self.assertEqual(resposta.status_code, 201)
        cliente = ClientePotencial.objects.get()
        self.assertEqual(cliente.nome, "Maria Souza")
        # Guardado só em dígitos e sem o +55, como `Lead.phone`.
        self.assertEqual(cliente.telefone, "69992264398")
        self.assertEqual(cliente.valor_estimado, Decimal("12500.00"))

    def test_acha_o_fechamento_em_qualquer_lugar_do_payload(self):
        """O Typebot põe o texto em lugares diferentes conforme o bloco que
        dispara o webhook. Procurar só numa chave esperada é a forma de a
        integração quebrar quando alguém mexer no fluxo."""
        resposta = self.postar({
            "messages": [{"type": "text", "content": "tudo certo então [FECHADO]"}],
            "variables": {
                "nome": "João",
                "whatsapp": "5569992264399",
                "projeto": "Automação de cobrança",
            },
        })

        self.assertEqual(resposta.status_code, 201)
        cliente = ClientePotencial.objects.get()
        self.assertEqual(cliente.nome, "João")
        self.assertEqual(cliente.telefone, "69992264399")

    def test_valor_em_formato_brasileiro(self):
        self.postar({
            "texto": "[FECHADO]",
            "nome": "Ana",
            "telefone": "69992264398",
            "descricao_projeto": "Site institucional",
            "valor_estimado": "R$ 12.500,00",
        })
        self.assertEqual(ClientePotencial.objects.get().valor_estimado, Decimal("12500.00"))

    def test_valor_ilegivel_nao_derruba_o_cadastro(self):
        """Fechamento sem valor continua sendo fechamento: perder o contato
        porque o robô não extraiu o número seria trocar um dado por todos."""
        self.postar({
            "texto": "[FECHADO]",
            "nome": "Ana",
            "telefone": "69992264398",
            "descricao_projeto": "Site institucional",
            "valor_estimado": "a combinar",
        })
        cliente = ClientePotencial.objects.get()
        self.assertIsNone(cliente.valor_estimado)

    def test_telefone_invalido_recusa(self):
        resposta = self.postar({
            "texto": "[FECHADO]",
            "nome": "Ana",
            "telefone": "123",
            "descricao_projeto": "Site institucional",
        })
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(ClientePotencial.objects.exists())

    def test_sem_nome_ou_descricao_recusa(self):
        resposta = self.postar({"texto": "[FECHADO]", "telefone": "69992264398"})
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(ClientePotencial.objects.exists())

    def test_json_quebrado_recusa(self):
        resposta = self.client.post(
            self.url, data="{isso não é json", content_type="application/json",
            HTTP_X_WEBHOOK_TOKEN=TOKEN,
        )
        self.assertEqual(resposta.status_code, 400)

    # --- duas vezes ---

    def test_mesma_conversa_reenviada_nao_duplica(self):
        """No WhatsApp o telefone é quem identifica a pessoa. Retentativa do
        Typebot, clique duplo no fluxo ou fechamento revisado têm que atualizar
        o registro — dois cadastros seriam duas conversas na fila."""
        corpo = {
            "texto": "[FECHADO]",
            "nome": "Maria",
            "telefone": "69992264398",
            "descricao_projeto": "Primeira versão",
            "valor_estimado": "10000",
        }
        self.assertEqual(self.postar(corpo).status_code, 201)

        corpo["descricao_projeto"] = "Escopo revisado na conversa"
        corpo["valor_estimado"] = "18000"
        resposta = self.postar(corpo)

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.json()["criado"])
        self.assertEqual(ClientePotencial.objects.count(), 1)
        cliente = ClientePotencial.objects.get()
        self.assertEqual(cliente.descricao_projeto, "Escopo revisado na conversa")
        self.assertEqual(cliente.valor_estimado, Decimal("18000"))

    def test_data_cadastro_e_o_created_at(self):
        self.postar({
            "texto": "[FECHADO]", "nome": "Ana", "telefone": "69992264398",
            "descricao_projeto": "Site",
        })
        cliente = ClientePotencial.objects.get()
        self.assertEqual(cliente.data_cadastro, cliente.created_at)
