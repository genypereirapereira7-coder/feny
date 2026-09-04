from django.test import SimpleTestCase

from apps.customers.validators import somente_digitos, validar_cnpj, validar_cpf


class ValidarCpfTests(SimpleTestCase):
    def test_cpf_valido_com_formatacao(self):
        self.assertTrue(validar_cpf("111.444.777-35"))

    def test_cpf_valido_so_digitos(self):
        self.assertTrue(validar_cpf("11144477735"))

    def test_digito_verificador_errado_e_invalido(self):
        self.assertFalse(validar_cpf("11144477736"))

    def test_todos_digitos_iguais_e_invalido(self):
        self.assertFalse(validar_cpf("11111111111"))

    def test_tamanho_errado_e_invalido(self):
        self.assertFalse(validar_cpf("123456789"))


class ValidarCnpjTests(SimpleTestCase):
    def test_cnpj_valido_com_formatacao(self):
        self.assertTrue(validar_cnpj("11.222.333/0001-81"))

    def test_cnpj_valido_so_digitos(self):
        self.assertTrue(validar_cnpj("11222333000181"))

    def test_digito_verificador_errado_e_invalido(self):
        self.assertFalse(validar_cnpj("11222333000182"))

    def test_todos_digitos_iguais_e_invalido(self):
        self.assertFalse(validar_cnpj("11111111111111"))


class SomenteDigitosTests(SimpleTestCase):
    def test_remove_pontuacao(self):
        self.assertEqual(somente_digitos("111.444.777-35"), "11144477735")

    def test_string_vazia(self):
        self.assertEqual(somente_digitos(""), "")
