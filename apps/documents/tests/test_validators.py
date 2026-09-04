from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.documents.validators import validar_arquivo


class ValidarArquivoAssinaturaTests(TestCase):
    def test_pdf_com_assinatura_correta_passa(self):
        arquivo = SimpleUploadedFile("x.pdf", b"%PDF-1.4\nresto do conteudo")
        validar_arquivo(arquivo)  # não levanta

    def test_pdf_sem_assinatura_e_recusado(self):
        arquivo = SimpleUploadedFile("x.pdf", b"nao e um pdf de verdade")
        with self.assertRaises(ValidationError):
            validar_arquivo(arquivo)

    def test_png_com_assinatura_correta_passa(self):
        arquivo = SimpleUploadedFile("x.png", b"\x89PNG\r\n\x1a\nresto")
        validar_arquivo(arquivo)

    def test_jpeg_disfarcado_de_png_e_recusado(self):
        arquivo = SimpleUploadedFile("x.png", b"\xff\xd8\xffresto de um jpeg de verdade")
        with self.assertRaises(ValidationError):
            validar_arquivo(arquivo)

    def test_txt_nao_tem_checagem_de_assinatura(self):
        arquivo = SimpleUploadedFile("x.txt", b"qualquer coisa aqui dentro")
        validar_arquivo(arquivo)  # não levanta — .txt não tem magic number confiável

    def test_ponteiro_do_arquivo_volta_pro_inicio_depois_de_validar(self):
        """A checagem lê os primeiros bytes pra conferir a assinatura — se
        não voltar o ponteiro, o `create()` do serializer leria o arquivo
        faltando o começo, e o checksum/tamanho gravados ficariam errados."""
        arquivo = SimpleUploadedFile("x.pdf", b"%PDF-1.4\nresto do conteudo")
        validar_arquivo(arquivo)
        self.assertEqual(arquivo.read(), b"%PDF-1.4\nresto do conteudo")
