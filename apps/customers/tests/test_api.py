from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.choices import PaymentMethod
from apps.customers.models import Customer, CustomerContact, CustomerKind
from apps.users.models import Role, User


class CustomerApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin1", password="senha-forte-123", role=Role.ADMIN)
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.outro_vendedor = User.objects.create_user(username="v2", password="senha-forte-123", role=Role.SALES)
        self.dev = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)

        self.payload_valido = {
            "kind": CustomerKind.INDIVIDUAL,
            "legal_name": "Fulano de Tal",
            "document": "111.444.777-35",
            "preferred_payment_method": PaymentMethod.BOLETO,
        }

    def test_vendedor_cria_cliente(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.post("/api/v1/customers/", self.payload_valido)

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        cliente = Customer.objects.get()
        self.assertEqual(cliente.created_by, self.vendedor)
        self.assertEqual(cliente.document, "11144477735")

    def test_cpf_invalido_devolve_400_nao_500(self):
        self.client.force_authenticate(self.vendedor)
        payload = {**self.payload_valido, "document": "111.444.777-36"}

        resposta = self.client.post("/api/v1/customers/", payload)

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("document", resposta.data)

    def test_documento_duplicado_devolve_400_nao_500(self):
        """Achado num smoke test da Fase 4: `UniqueValidator` automático do
        DRF comparava o valor bruto (com pontuação) contra o normalizado no
        banco, nunca batia, e o duplicado só estourava dentro de `.save()`
        como 500. `validate()` agora checa unicidade manualmente, depois de
        normalizar."""
        self.client.force_authenticate(self.vendedor)
        self.client.post("/api/v1/customers/", self.payload_valido)

        resposta = self.client.post("/api/v1/customers/", {**self.payload_valido, "legal_name": "Outro Nome"})

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("document", resposta.data)
        self.assertEqual(Customer.objects.count(), 1)

    def test_cria_empresa_com_cnpj_formatado(self):
        """Achado no mesmo smoke test: `document` do model tem `max_length=14`
        (valor normalizado), mas o `ModelSerializer` herdava esse limite pro
        campo de entrada — um CNPJ formatado com pontuação (18 caracteres)
        era recusado por tamanho antes de `validate()` normalizar."""
        self.client.force_authenticate(self.vendedor)
        payload = {
            "kind": CustomerKind.COMPANY,
            "legal_name": "Empresa Fulano LTDA",
            "document": "11.222.333/0001-81",
            "preferred_payment_method": PaymentMethod.BOLETO,
        }

        resposta = self.client.post("/api/v1/customers/", payload)

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["document"], "11222333000181")

    def test_desenvolvedor_nao_cria_cliente(self):
        self.client.force_authenticate(self.dev)
        resposta = self.client.post("/api/v1/customers/", self.payload_valido)
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_qualquer_papel_autenticado_le_clientes(self):
        self.client.force_authenticate(self.dev)
        resposta = self.client.get("/api/v1/customers/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_vendedor_edita_cliente_que_criou(self):
        self.client.force_authenticate(self.vendedor)
        criado = self.client.post("/api/v1/customers/", self.payload_valido).data

        resposta = self.client.patch(f"/api/v1/customers/{criado['id']}/", {"phone": "11999999999"})
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_vendedor_nao_edita_cliente_de_outro_vendedor(self):
        self.client.force_authenticate(self.outro_vendedor)
        criado = self.client.post("/api/v1/customers/", self.payload_valido).data

        self.client.force_authenticate(self.vendedor)
        resposta = self.client.patch(f"/api/v1/customers/{criado['id']}/", {"phone": "11999999999"})
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_vendedor_nao_exclui_cliente(self):
        self.client.force_authenticate(self.vendedor)
        criado = self.client.post("/api/v1/customers/", self.payload_valido).data

        resposta = self.client.delete(f"/api/v1/customers/{criado['id']}/")
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_exclui_cliente(self):
        self.client.force_authenticate(self.vendedor)
        criado = self.client.post("/api/v1/customers/", self.payload_valido).data

        self.client.force_authenticate(self.admin)
        resposta = self.client.delete(f"/api/v1/customers/{criado['id']}/")
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)


class CustomerContactApiTests(APITestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)
        self.cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )

    def test_cria_contato_do_cliente(self):
        self.client.force_authenticate(self.vendedor)
        resposta = self.client.post(
            "/api/v1/customer-contacts/",
            {"customer": str(self.cliente.id), "name": "Fulaninho", "role": "financeiro"},
        )
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomerContact.objects.count(), 1)

    def test_filtra_contatos_por_cliente(self):
        CustomerContact.objects.create(customer=self.cliente, name="Contato 1")
        outro_cliente = Customer.objects.create(
            kind=CustomerKind.COMPANY, legal_name="Outra Empresa", document="11222333000181",
            preferred_payment_method=PaymentMethod.CARD, created_by=self.vendedor,
        )
        CustomerContact.objects.create(customer=outro_cliente, name="Contato 2")

        self.client.force_authenticate(self.vendedor)
        resposta = self.client.get(f"/api/v1/customer-contacts/?customer={self.cliente.id}")

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resposta.data["results"]), 1)
        self.assertEqual(resposta.data["results"][0]["name"], "Contato 1")
