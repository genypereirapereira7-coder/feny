from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.choices import PaymentMethod
from apps.customers.models import Customer, CustomerKind
from apps.users.models import Role, User


class CustomerValidationTests(TestCase):
    def setUp(self):
        self.vendedor = User.objects.create_user(username="v1", password="senha-forte-123", role=Role.SALES)

    def test_pessoa_fisica_com_cpf_valido_salva(self):
        cliente = Customer(
            kind=CustomerKind.INDIVIDUAL,
            legal_name="Fulano de Tal",
            document="111.444.777-35",
            preferred_payment_method=PaymentMethod.BOLETO,
            created_by=self.vendedor,
        )
        cliente.save()

        cliente.refresh_from_db()
        self.assertEqual(cliente.document, "11144477735")  # normalizado, só dígitos

    def test_pessoa_fisica_com_cpf_invalido_recusa(self):
        cliente = Customer(
            kind=CustomerKind.INDIVIDUAL,
            legal_name="Fulano de Tal",
            document="111.444.777-36",
            preferred_payment_method=PaymentMethod.BOLETO,
            created_by=self.vendedor,
        )
        with self.assertRaises(ValidationError):
            cliente.save()

    def test_pessoa_juridica_com_cnpj_valido_salva(self):
        cliente = Customer(
            kind=CustomerKind.COMPANY,
            legal_name="Empresa Fulano LTDA",
            document="11.222.333/0001-81",
            preferred_payment_method=PaymentMethod.CARD,
            created_by=self.vendedor,
        )
        cliente.save()
        self.assertEqual(Customer.objects.count(), 1)

    def test_pessoa_juridica_com_cpf_e_recusada(self):
        """Documento de 11 dígitos válido como CPF não serve pra kind=COMPANY."""
        cliente = Customer(
            kind=CustomerKind.COMPANY,
            legal_name="Empresa Errada",
            document="111.444.777-35",
            preferred_payment_method=PaymentMethod.CARD,
            created_by=self.vendedor,
        )
        with self.assertRaises(ValidationError):
            cliente.save()

    def test_documento_duplicado_e_recusado(self):
        Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Primeiro", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
        )
        with self.assertRaises(ValidationError):
            Customer(
                kind=CustomerKind.INDIVIDUAL, legal_name="Segundo", document="111.444.777-35",
                preferred_payment_method=PaymentMethod.BOLETO, created_by=self.vendedor,
            ).save()
