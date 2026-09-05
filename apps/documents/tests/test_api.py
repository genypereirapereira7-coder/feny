import hashlib
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document, DocumentCategory
from apps.users.models import Role, User

_MEDIA_TEMP = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=_MEDIA_TEMP)
class DocumentUploadApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_TEMP, ignore_errors=True)

    def setUp(self):
        self.usuario = User.objects.create_user(username="dev1", password="senha-forte-123", role=Role.DEVELOPER)
        self.client.force_authenticate(self.usuario)

    def test_upload_calcula_metadados_no_servidor(self):
        conteudo = b"%PDF-1.4\nconteudo de teste do pdf"
        arquivo = SimpleUploadedFile("contrato.pdf", conteudo, content_type="application/pdf")

        resposta = self.client.post(
            "/api/v1/documents/",
            {"category": DocumentCategory.CONTRACT, "file": arquivo},
            format="multipart",
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        documento = Document.objects.get()
        self.assertEqual(documento.original_filename, "contrato.pdf")
        self.assertEqual(documento.size_bytes, len(conteudo))
        self.assertEqual(documento.checksum_sha256, hashlib.sha256(conteudo).hexdigest())
        self.assertEqual(documento.uploaded_by, self.usuario)

    def test_extensao_nao_permitida_e_recusada(self):
        arquivo = SimpleUploadedFile("virus.exe", b"conteudo", content_type="application/octet-stream")

        resposta = self.client.post(
            "/api/v1/documents/",
            {"category": DocumentCategory.OTHER, "file": arquivo},
            format="multipart",
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Document.objects.count(), 0)

    def test_conteudo_que_nao_bate_com_a_extensao_e_recusado(self):
        """Extensão `.pdf` certa, header HTTP `content_type` certo, mas os
        bytes de verdade não são de um PDF — a checagem por assinatura (Fase
        10) pega isso mesmo quando extensão e `content_type` mentem juntos."""
        arquivo = SimpleUploadedFile(
            "fingido.pdf", b"isto nao comeca com a assinatura de um pdf de verdade",
            content_type="application/pdf",
        )

        resposta = self.client.post(
            "/api/v1/documents/",
            {"category": DocumentCategory.OTHER, "file": arquivo},
            format="multipart",
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Document.objects.count(), 0)

    def test_arquivo_maior_que_o_limite_e_recusado(self):
        conteudo_grande = b"%PDF-1.4\n" + b"x" * (21 * 1024 * 1024)  # acima do limite de 20MB
        arquivo = SimpleUploadedFile("grande.pdf", conteudo_grande, content_type="application/pdf")

        resposta = self.client.post(
            "/api/v1/documents/",
            {"category": DocumentCategory.OTHER, "file": arquivo},
            format="multipart",
        )

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_campos_derivados_nao_sao_aceitos_do_cliente(self):
        """Mandar `checksum_sha256`/`size_bytes` no payload não deve ter efeito —
        são sempre recalculados a partir do arquivo de verdade."""
        conteudo = b"%PDF-1.4\nconteudo real"
        arquivo = SimpleUploadedFile("nota.pdf", conteudo, content_type="application/pdf")

        resposta = self.client.post(
            "/api/v1/documents/",
            {
                "category": DocumentCategory.RECEIPT,
                "file": arquivo,
                "checksum_sha256": "forjado",
                "size_bytes": 999999,
            },
            format="multipart",
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        documento = Document.objects.get()
        self.assertEqual(documento.checksum_sha256, hashlib.sha256(conteudo).hexdigest())
        self.assertEqual(documento.size_bytes, len(conteudo))

    def test_filtra_por_projeto(self):
        """Frontend §26 — aba Documentos da tela de projeto."""
        from apps.core.choices import PaymentMethod, ProjectType
        from apps.customers.models import Customer, CustomerKind
        from apps.projects.models import Project, ProjectStatus
        from apps.quotations.models import Quotation

        cliente = Customer.objects.create(
            kind=CustomerKind.INDIVIDUAL, legal_name="Fulano", document="11144477735",
            preferred_payment_method=PaymentMethod.BOLETO, created_by=self.usuario,
        )
        orcamento = Quotation.objects.create(
            customer=cliente, sales_rep=self.usuario, service_type=ProjectType.WEBSITE,
            description="x", amount="1000.00",
        )
        projeto = Project.objects.create(
            customer=cliente, quotation=orcamento, name="Projeto X", project_type=ProjectType.WEBSITE,
            responsible=self.usuario, amount="1000.00", status=ProjectStatus.APPROVED,
        )
        Document.objects.create(
            project=projeto, category=DocumentCategory.PROJECT_FILE, original_filename="x.pdf",
            mime_type="application/pdf", size_bytes=1, checksum_sha256="a", uploaded_by=self.usuario,
        )
        Document.objects.create(
            category=DocumentCategory.OTHER, original_filename="y.pdf",
            mime_type="application/pdf", size_bytes=1, checksum_sha256="b", uploaded_by=self.usuario,
        )

        resposta = self.client.get(f"/api/v1/documents/?project={projeto.id}")
        self.assertEqual(len(resposta.data["results"]), 1)
        self.assertEqual(resposta.data["results"][0]["original_filename"], "x.pdf")
