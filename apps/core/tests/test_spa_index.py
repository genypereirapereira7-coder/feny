import tempfile
from pathlib import Path

from django.test import TestCase, override_settings


class SpaIndexTests(TestCase):
    """`spa_index` (ARCHITECTURE.md — deploy de serviço único no Railway):
    duas páginas no mesmo diretório servido, e a rota decide qual.

    A vitrine (`index.html`, estática) fica na raiz; o painel React
    (`painel.html`) responde por `/painel`, `/login` e pelas rotas antigas.
    O F5 direto em `/painel/projetos/1` precisa devolver o app inteiro — é
    o React Router quem conhece essa rota, não o Django."""

    def _montar(self, tmp, **arquivos):
        frontend_dist = Path(tmp) / "frontend_dist"
        frontend_dist.mkdir()
        for nome, conteudo in arquivos.items():
            (frontend_dist / nome).write_text(conteudo)
        return frontend_dist

    def test_raiz_serve_a_vitrine(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._montar(tmp, **{"index.html": "<html>vitrine</html>", "painel.html": "<html>painel</html>"})
            with override_settings(BASE_DIR=Path(tmp)):
                resposta = self.client.get("/")

        self.assertEqual(resposta.content.decode(), "<html>vitrine</html>")

    def test_painel_serve_o_bundle_do_react(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._montar(tmp, **{"index.html": "<html>vitrine</html>", "painel.html": "<html>painel</html>"})
            with override_settings(BASE_DIR=Path(tmp)):
                for rota in ("/painel", "/painel/projetos/1", "/login", "/2fa/configurar"):
                    with self.subTest(rota=rota):
                        self.assertEqual(self.client.get(rota).content.decode(), "<html>painel</html>")

    def test_comecar_serve_a_pagina_do_formulario(self):
        """A vitrine tem duas páginas: a landing na raiz e `/comecar`, com o
        formulário. Com e sem barra no fim — as duas formas circulam por aí."""
        with tempfile.TemporaryDirectory() as tmp:
            self._montar(
                tmp,
                **{
                    "index.html": "<html>vitrine</html>",
                    "comecar.html": "<html>comecar</html>",
                    "painel.html": "<html>painel</html>",
                },
            )
            with override_settings(BASE_DIR=Path(tmp)):
                for rota in ("/comecar", "/comecar/"):
                    with self.subTest(rota=rota):
                        self.assertEqual(self.client.get(rota).content.decode(), "<html>comecar</html>")

    def test_rota_antiga_ainda_cai_no_painel(self):
        """Bookmark salvo antes de o painel mudar de lugar (`/clientes`) tem
        que chegar ao React, que é quem sabe redirecionar pra `/painel/...`.
        Caindo na vitrine, o link antigo simplesmente abriria a home."""
        with tempfile.TemporaryDirectory() as tmp:
            self._montar(tmp, **{"index.html": "<html>vitrine</html>", "painel.html": "<html>painel</html>"})
            with override_settings(BASE_DIR=Path(tmp)):
                resposta = self.client.get("/financeiro/cobrancas")

        self.assertEqual(resposta.content.decode(), "<html>painel</html>")

    def test_serve_pagina_quando_frontend_buildado(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._montar(tmp, **{"index.html": "<html>vitrine</html>"})

            with override_settings(BASE_DIR=Path(tmp)):
                resposta = self.client.get("/")

            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.content.decode(), "<html>vitrine</html>")

    def test_404_texto_quando_frontend_nao_buildado(self):
        """Sem build, a resposta é um aviso legível — não uma exceção de
        arquivo ausente.

        O `BASE_DIR` aponta pra um diretório vazio de propósito. Antes este
        teste dependia de `frontend_dist/` não existir no repositório, o que é
        verdade no CI e deixa de ser no instante em que alguém monta o
        frontend na própria máquina: o teste passava ou falhava conforme o
        estado da pasta de quem rodou."""
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(BASE_DIR=Path(tmp)):
                resposta = self.client.get("/qualquer-rota")
        self.assertEqual(resposta.status_code, 404)
        self.assertIn(b"Frontend n\xc3\xa3o buildado", resposta.content)

    def test_prévia_de_link_vira_endereco_absoluto(self):
        """WhatsApp e Facebook descartam `og:image` com caminho relativo — a
        prévia sairia sem imagem nenhuma. O endereço é montado a partir do
        host da requisição pra valer em qualquer domínio sem configuração."""
        html = (
            "<html><head>"
            '<meta property="og:image" content="/midia/og.jpg" />'
            '<meta name="twitter:image" content="/midia/og.jpg" />'
            "</head></html>"
        )
        with tempfile.TemporaryDirectory() as tmp:
            self._montar(tmp, **{"index.html": html})

            with override_settings(BASE_DIR=Path(tmp)):
                resposta = self.client.get("/", HTTP_HOST="feny.com.br")

        corpo = resposta.content.decode()
        self.assertIn('content="http://feny.com.br/midia/og.jpg"', corpo)
        self.assertNotIn('content="/midia/og.jpg"', corpo)
        # `og:url` não mora no HTML: é a única marca que muda de rota pra rota.
        self.assertIn('<meta property="og:url" content="http://feny.com.br/" />', corpo)

    def test_prévia_de_link_ignora_query_string(self):
        """A prévia de um link com `?utm_source=...` tem que apontar pro mesmo
        endereço que o link sem ela — senão cada campanha vira uma URL
        diferente pro mesmo conteúdo."""
        with tempfile.TemporaryDirectory() as tmp:
            self._montar(tmp, **{"index.html": "<html><head></head></html>"})

            with override_settings(BASE_DIR=Path(tmp)):
                resposta = self.client.get("/?utm_source=whatsapp", HTTP_HOST="feny.com.br")

        self.assertIn('content="http://feny.com.br/" />', resposta.content.decode())

    def test_nao_intercepta_rotas_de_api(self):
        resposta = self.client.get("/health/")
        self.assertEqual(resposta["Content-Type"], "application/json")
