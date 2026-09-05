import tempfile
from pathlib import Path

from django.test import TestCase, override_settings


class SpaIndexTests(TestCase):
    """`spa_index` (ARCHITECTURE.md — deploy de serviço único no Railway):
    qualquer rota que não seja admin/api/health cai no `index.html` do React,
    pra rotas de verdade do React Router (`/clientes`, `/projetos/1`)
    funcionarem num F5 direto, não só navegando pelo próprio app."""

    def test_serve_index_quando_frontend_buildado(self):
        with tempfile.TemporaryDirectory() as tmp:
            frontend_dist = Path(tmp) / "frontend_dist"
            frontend_dist.mkdir()
            (frontend_dist / "index.html").write_text("<html>spa</html>")

            with override_settings(BASE_DIR=Path(tmp)):
                resposta = self.client.get("/clientes")

            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.content.decode(), "<html>spa</html>")

    def test_404_texto_quando_frontend_nao_buildado(self):
        # Estado real deste repositório em teste (sem Dockerfile rodando) —
        # `frontend_dist/index.html` não existe, então cai no aviso, não numa
        # exceção de arquivo ausente.
        resposta = self.client.get("/qualquer-rota-do-react")
        self.assertEqual(resposta.status_code, 404)
        self.assertIn(b"Frontend n\xc3\xa3o buildado", resposta.content)

    def test_nao_intercepta_rotas_de_api(self):
        resposta = self.client.get("/health/")
        self.assertEqual(resposta["Content-Type"], "application/json")
