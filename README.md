# Feny

Plataforma interna de **gestão comercial, operacional e financeira** da Feny — uma software house que presta serviços de desenvolvimento sob medida (sistemas, automações, sites, PWAs, apps, SaaS e integrações) para outras empresas.

## O que ela resolve

Cada projeto entregue gera dinheiro em momentos diferentes, e nenhum deles pode depender de alguém lembrar manualmente:

| # | Cobrança | Quando | Recorrência |
|---|---|---|---|
| 1 | **Sinal** | Antes do início do desenvolvimento | Única — 30% do valor |
| 2 | **Saldo** | Após conclusão e aceite do cliente | Única — 70% restante |
| 3 | **Mensalidade** | Serviços contínuos (hospedagem, manutenção, SaaS) | Recorrente |
| 4 | **Alteração de escopo** | Quando o cliente pede mudança | Sob demanda |

Em torno disso, a plataforma centraliza clientes, orçamentos e sua aprovação, projetos e seu fluxo de entrega, financeiro (receitas, despesas, contas a receber, comissões), cobrança automatizada via **Mercado Pago**, avisos via **WhatsApp** (Evolution API), documentos, usuários/permissões e auditoria.

Não é um produto vendido a terceiros — é o núcleo operacional interno da Feny, usado exclusivamente pela própria empresa.

## Estado atual

✅ **Fase 10 de 10 concluída — roadmap inteiro implementado.** A plataforma cobre o ciclo completo: cliente → orçamento → aprovação → projeto → cobrança (manual ou via Mercado Pago) → pagamento confirmado (webhook idempotente) → comissão → aviso automático por WhatsApp → recorrência → dashboard por papel. Esta última fase foi hardening: 2FA obrigatório para admin/gerente/financeiro, rate limiting no login e no webhook, upload validado até pelos bytes de verdade do arquivo (não só extensão), índices nas consultas mais pesadas, backup com restauração testada de verdade (não só "existe uma cópia"), health check que confere o banco, e CI (lint → testes → checagem de migrations → build) em `.github/workflows/ci.yml`. Detalhes de segurança em [SECURITY.md](SECURITY.md).

Depois do roadmap, entrou o **site institucional público** — ver a seção abaixo.

A arquitetura técnica completa está em **[ARCHITECTURE.md](ARCHITECTURE.md)** — domínios, modelos de dados, máquinas de estado, regras de negócio (30/70, comissão, idempotência), integrações externas, segurança e roadmap de implementação por fases.

## Stack

Python · Django · Django REST Framework · PostgreSQL · Monólito modular

## O site público

**A vitrine não é React.** É `landing/` — `index.html`, `style.css`, `script.js` e o vídeo, sem build e sem framework. O painel continua sendo o app React. Um deploy só, duas páginas, separadas pela rota:

| Rota | O que é | De onde vem |
|---|---|---|
| `/` | Vitrine pública: o vídeo do topo, serviços, como funciona, projetos, investimento, dúvidas e contato | `landing/index.html` |
| `/painel/...` | O sistema interno inteiro (dashboard, clientes, leads, orçamentos, projetos, financeiro…) | build do React (`painel.html`) |
| `/login`, `/2fa/...` | Entrada do painel | build do React |

Quem chega pelo Google **não baixa uma linha do JavaScript do painel** — nem o React. São ~7 KB de script próprio contra os ~130 KB do bundle do sistema, e é essa diferença que decide se a pessoa espera a página abrir. Links antigos (`/clientes`, `/financeiro/cobrancas`…) continuam caindo no painel, que os redireciona pro caminho novo — bookmark salvo não quebrou.

Quem escolhe qual página entregar é `apps/core/views.py::spa_index`, por prefixo de rota. E quem monta o diretório servido é `scripts/montar_frontend.sh`: copia o build do React, renomeia o `index.html` dele pra `painel.html` (liberando a raiz) e põe a landing por cima. O Dockerfile roda **o mesmo script** — deploy não tem um jeito próprio de arrumar arquivo que ninguém testa até quebrar em produção.

### O topo: o mouse é a linha do tempo

O vídeo de fundo nunca toca sozinho. Ele fica parado e o `script.js` diz em que segundo ele deve estar, a partir da posição horizontal do ponteiro — esquerda é o começo, direita é o fim. Entre o que o mouse pede e o que o vídeo recebe existe uma suavização; sem ela o vídeo copia o tremor da mão.

O texto acompanha: são três capítulos (a conversa, o orçamento, a entrega) que trocam **no meio de cada dissolvência da montagem** (6,5 s e 13 s de 20,5 s), não em 33% e 66%. Meio segundo fora disso e o olho percebe que imagem e texto são coisas independentes — é o que estraga a ilusão.

Três detalhes que não são enfeite:

- **Keyframe a cada 10 quadros** no vídeo (`-g 10`). Num vídeo comum, com keyframe a cada 2–5 s, arrastar trava: cada salto obriga o navegador a decodificar desde o keyframe anterior. Custou ~40% de tamanho e é o que compra a suavidade.
- **A suavização é corrigida pelo tempo entre quadros**, não aplicada como fração fixa. Sem isso o efeito roda com o dobro da velocidade num monitor de 120 Hz.
- **Um `play()` seguido de `pause()`** ao carregar. Parece inútil; sem ele o iOS não desenha quadro nenhum de um vídeo que nunca tocou, por mais que o `currentTime` mude.

Quem navega por teclado move a linha do tempo com as setas, e quem está no celular arrasta o dedo. Com "reduzir movimento" ligado, nada disso se mexe.

**Formulário de contato → lead no sistema.** A landing posta em `POST /api/v1/public/contact/`, o único endpoint da plataforma sem autenticação. Cada envio vira um `Lead` que aparece em **Comercial → Leads do site**, onde alguém atende (`entrei em contato` → `qualificar` → `virou cliente` / `descartar`), sempre com auditoria. O endpoint tem rate limit por IP (5/min), campo-armadilha contra robô e janela anti-duplicata; a validação de cada campo existe nas duas pontas — na tela pra avisar cedo, no backend porque é ele quem decide. Detalhes em [ARCHITECTURE.md §6.11](ARCHITECTURE.md).

### O vídeo do topo

`landing/video.mp4` (1920×1080, 20,5 s, 5,3 MB) é a junção de três gravações de banco de imagens — mãos digitando, caneta numa agenda em tablet e um painel rodando na tela — uma pra cada capítulo do texto, com dissolvência de 1 s entre elas e a mesma correção de cor nas três (senão uma chega quente, outra azulada, e o corte denuncia que são três vídeos diferentes):

```bash
# 1. cada trecho, normalizado pro mesmo formato e com a mesma cor
GRADE="eq=contrast=1.08:saturation=0.82:gamma=0.97,colortemperature=temperature=5200"
ffmpeg -ss 1 -t 7 -i digitando.mp4 -vf "scale=1920:1080,fps=30,$GRADE" -c:v libx264 -crf 14 -an s1.mp4
# (idem pros outros dois)

# 2. junta com dissolvência e grava com keyframe denso, pro scrubbing não travar
ffmpeg -i s1.mp4 -i s2.mp4 -i s3.mp4 -filter_complex \
  "[0][1]xfade=transition=fade:duration=1:offset=6[x];[x][2]xfade=transition=fade:duration=1:offset=12.5[v]" \
  -map "[v]" -c:v libx264 -crf 27 -preset slow -pix_fmt yuv420p \
  -g 10 -keyint_min 10 -sc_threshold 0 -movflags +faststart -an video.mp4
```

Se trocar o vídeo, ajuste `LIMITES` no `script.js`: são as fronteiras dos capítulos, e elas vêm da montagem, não de frações redondas.

### A imagem da prévia de link

`frontend/public/midia/og.jpg` (1200×630, 135 KB) é o que aparece quando alguém cola o link da Feny no WhatsApp, no Facebook ou no LinkedIn. Sai do mesmo banner que originou o vídeo — só que inteiro, com manchete, telefone e logo legíveis, que é exatamente o conteúdo que uma prévia precisa ter e uma página não (dentro do site aquela manchete repetiria a que já está no topo).

```bash
ffmpeg -i banner.png -vf "scale=1200:-2,crop=1200:630:0:22" -q:v 4 og.jpg
```

O `index.html` guarda o caminho **relativo** (`/midia/og.jpg`) e o Django o transforma em endereço absoluto na hora de servir (`apps/core/views.py::spa_index`), montado a partir do host da requisição. WhatsApp e Facebook descartam caminho relativo — a prévia sairia sem imagem — e o domínio muda entre `localhost`, Railway e um domínio próprio, então um endereço fixo no HTML seria escolher um dos três pra funcionar e descobrir os outros dois quebrados só quando alguém colasse o link. A `og:url` é injetada pelo mesmo caminho, sem a query string, pra que o link de campanha (`?utm_source=...`) aponte pro mesmo lugar que o link limpo.

## Como rodar localmente

Com Docker:

```bash
docker compose up
```

Sem Docker (Postgres local já rodando):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env   # ajuste DATABASE_URL se necessário
python manage.py migrate
python manage.py create_default_groups
python manage.py createsuperuser
python manage.py runserver
```

### As duas frentes do frontend

A vitrine não tem build: é arquivo estático. Qualquer servidor serve, e a porta importa — a `4200` é a que o `script.js` usa pra saber que está em desenvolvimento e falar com a API em `localhost:8001` (em produção é tudo mesma origem):

```bash
cd landing && python3 -m http.server 4200
```

O painel é o Vite de sempre:

```bash
cd frontend && npm run dev      # http://localhost:5173/painel
```

Pra ver as duas como em produção — mesma origem, uma página só respondendo por rota — monte o diretório servido e deixe o Django entregar tudo:

```bash
cd frontend && npm run build && cd ..
./scripts/montar_frontend.sh
python manage.py runserver      # / é a vitrine, /painel é o sistema
```

Testes e lint:

```bash
python manage.py test
ruff check apps config manage.py
cd frontend && npx tsc -b --noEmit && npm run build
```

Login (API): `POST /api/v1/auth/token/` com `username`/`password` (+ `otp_code` se 2FA estiver ativo) — devolve `access`/`refresh`. Identidade atual: `GET /api/v1/users/me/`. Admin/gerente/financeiro precisam configurar 2FA (`/auth/2fa/setup/` + `/auth/2fa/confirm/`) — ver [SECURITY.md](SECURITY.md).

Envio de notificações pendentes (WhatsApp) e geração de cobranças recorrentes — rodar via cron em produção, chamar manualmente em dev:

```bash
python manage.py dispatch_notifications
python manage.py generate_recurring_charges
```

## Deploy no Railway

> A tela de login está ativa por padrão — qualquer visitante sem sessão cai
> nela. `VITE_AUTO_LOGIN_USERNAME`/`_PASSWORD` (opcional, só em
> `frontend/.env`, nunca commitado) pulam essa tela **só na máquina onde essa
> variável existe**: sem `.env`, o Vite elimina esse código inteiro do bundle
> (dead-code elimination — nada de credencial ou nome de variável sobra no
> JS enviado ao navegador). **Nunca configure essas duas variáveis nas
> Variables do serviço no Railway** — lá elas ficariam embutidas em texto
> puro no JavaScript que qualquer visitante pode ler.

**Um serviço só.** O `Dockerfile` da raiz builda o React (estágio 1, Node) e
o Django do estágio 2 serve tanto a API quanto os arquivos do frontend já
prontos — mesmo domínio pros dois, sem CORS entre eles, sem precisar de um
segundo serviço Railway. `config/urls.py` manda qualquer rota que não seja
`admin/`/`api/`/`health/` pro `index.html` do React (`apps/core/views.py::spa_index`),
e o `WhiteNoiseMiddleware` serve os arquivos estáticos (`/assets/...`,
`favicon.svg`) direto da pasta que o Dockerfile copiou (`frontend_dist/`).

1. **Banco**: no projeto Railway, adicione um plugin **PostgreSQL** — ele
   expõe `DATABASE_URL` sozinho, sem precisar copiar nada manualmente.
2. **Serviço**: novo serviço a partir do repo (Root Directory pode ficar em
   branco/`/`, é a raiz mesmo). Railway detecta o `Dockerfile`. Variáveis:
   - `DJANGO_SETTINGS_MODULE=config.settings.production`
   - `SECRET_KEY` — gere com `python -c "import secrets; print(secrets.token_urlsafe(50))"`
     (sem isto, roda com um fallback inseguro em vez de quebrar — mas defina
     de verdade)
   - `DATABASE_URL` — referencie a variável do plugin Postgres (`${{Postgres.DATABASE_URL}}`)
   - `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` — normalmente **nem precisa
     definir**: `production.py` já inclui sozinho o domínio que o próprio
     Railway gera (`RAILWAY_PUBLIC_DOMAIN`, injetado automaticamente). Só
     defina à mão se usar um domínio próprio.
   - `CORS_ALLOWED_ORIGINS` não é necessário aqui — API e frontend estão no
     mesmo domínio, então não existe requisição cross-origin nenhuma pra
     liberar.
   - `DEFAULT_ACCOUNT_PASSWORD` — a senha da conta única do sistema (usuário
     fixo `gerente`, tela de login só pede senha). **Obrigatória**: sem ela,
     `ensure_default_account` não cria/atualiza a conta em nenhum deploy, e o
     login falha (foi exatamente isto que aconteceu no primeiro deploy: a
     senha só existia no banco local, nunca no do Railway). Trocar esta
     variável e fazer redeploy também serve pra trocar a senha depois.
   - Opcional: `DEFAULT_ACCOUNT_USERNAME` (default `gerente`) — só se quiser
     outro nome de usuário fixo por trás da tela.
   - Opcionais: `MERCADOPAGO_*`, `EVOLUTION_API_*`, `SENTRY_DSN` (ver `.env.example`)
   - `PORT` não precisa ser definida — o Railway injeta e o
     `docker-entrypoint.sh` já lê `$PORT`. O mesmo entrypoint roda `migrate`,
     `create_default_groups` e `ensure_default_account` a cada deploy — não
     é um passo manual à parte, nem depende de rodar nada pelo Railway CLI.
   - `VITE_API_BASE_URL` também não precisa ser definida: o build já usa
     `/api/v1` (caminho relativo, mesmo domínio) por padrão. Só sobrescreva
     via `--build-arg`/variável de build se a API algum dia morar num
     domínio à parte.
3. Deploy. Quando terminar, gere o domínio público em **Settings →
   Networking → Generate Domain** — é a mesma URL pra tela do sistema e pra
   API (`https://<domínio>/api/v1/...`). Primeiro login: só a senha de
   `DEFAULT_ACCOUNT_PASSWORD` — o sistema pede pra configurar 2FA na hora
   (conta `MANAGER`, 2FA obrigatório por papel).

Se o serviço não buildar a partir do `Dockerfile` automaticamente, confira
em Settings → Build se o **Builder** está como "Dockerfile" (não
"Nixpacks") — Railway às vezes mantém a escolha antiga de builder de quando
o serviço foi criado; force manualmente se isso acontecer.

## Roadmap

- [x] **Fase 1** — Fundação (Django, PostgreSQL, Custom User, autenticação, RBAC base, Docker)
- [x] **Fase 2** — Clientes (CRUD, contatos, documentos com validação de CPF/CNPJ)
- [x] **Fase 3** — Comercial (orçamentos, aprovação, auditoria)
- [x] **Fase 4** — Projetos e máquina de estado (geração a partir de orçamento aprovado)
- [x] **Fase 5** — Financeiro (Charge/Payment/Revenue/Expense/Commission, manual/interno)
- [x] **Fase 6** — Mercado Pago (cobrança, webhook, idempotência, verificação server-to-server)
- [x] **Fase 7** — Evolution API (notificações de cobrança emitida e pagamento confirmado)
- [x] **Fase 8** — Cobrança recorrente (`RecurringSubscription`, geração automática de `Charge RECURRING`)
- [x] **Fase 9** — Dashboard e relatórios (resumo por papel, receita/despesa por mês)
- [x] **Fase 10** — Hardening (2FA, rate limiting, upload por magic number, índices, backup testado, health check, CI)
- [x] **Site institucional** — página pública em `/`, painel movido pra `/painel`, formulário de contato virando lead no sistema (`apps/leads`)

---

Projeto proprietário de uso interno.
