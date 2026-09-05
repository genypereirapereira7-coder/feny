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

A arquitetura técnica completa está em **[ARCHITECTURE.md](ARCHITECTURE.md)** — domínios, modelos de dados, máquinas de estado, regras de negócio (30/70, comissão, idempotência), integrações externas, segurança e roadmap de implementação por fases.

## Stack

Python · Django · Django REST Framework · PostgreSQL · Monólito modular

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

Testes e lint:

```bash
python manage.py test
ruff check apps config manage.py
```

Login (API): `POST /api/v1/auth/token/` com `username`/`password` (+ `otp_code` se 2FA estiver ativo) — devolve `access`/`refresh`. Identidade atual: `GET /api/v1/users/me/`. Admin/gerente/financeiro precisam configurar 2FA (`/auth/2fa/setup/` + `/auth/2fa/confirm/`) — ver [SECURITY.md](SECURITY.md).

Envio de notificações pendentes (WhatsApp) e geração de cobranças recorrentes — rodar via cron em produção, chamar manualmente em dev:

```bash
python manage.py dispatch_notifications
python manage.py generate_recurring_charges
```

## Deploy no Railway

> ⚠️ **Antes de publicar de verdade**: a tela de login do frontend está
> desligada por conveniência de desenvolvimento (`frontend/src/App.tsx` tem a
> rota `/login` comentada; `ProtectedRoute.tsx` não redireciona mais pra ela).
> Publicar assim deixa o site sem nenhum jeito de autenticar quem visitar —
> travado numa tela de "não foi possível entrar automaticamente" pra qualquer
> pessoa, ou, se `VITE_AUTO_LOGIN_USERNAME`/`_PASSWORD` forem configuradas no
> Railway, com a credencial de um usuário real embutida em texto puro no
> JavaScript que qualquer visitante pode ler. Religue a tela de login (reverta
> as duas mudanças acima) antes de expor a URL pra alguém além de você.

O repositório tem um `Dockerfile` + `railway.json` próprio em cada metade —
raiz (backend) e `frontend/` (frontend) — de propósito: cada serviço builda
via **Docker**, não via detecção automática de linguagem (Nixpacks), pra não
depender de heurística nenhuma sobre o que tem em cada pasta. São **dois
serviços Railway apontando pro mesmo repositório**, cada um com uma "Root
Directory" diferente:

1. **Banco**: no projeto Railway, adicione um plugin **PostgreSQL** — ele
   expõe `DATABASE_URL` sozinho, sem precisar copiar nada manualmente.
2. **Backend** — novo serviço a partir do repo, **Root Directory `/`**
   (a raiz mesmo — deixe em branco ou digite `/`). Railway detecta o
   `Dockerfile` da raiz. Variáveis:
   - `DJANGO_SETTINGS_MODULE=config.settings.production`
   - `SECRET_KEY` — gere com `python -c "import secrets; print(secrets.token_urlsafe(50))"`
     (sem isto, roda com um fallback inseguro em vez de quebrar — mas defina
     de verdade)
   - `DATABASE_URL` — referencie a variável do plugin Postgres (`${{Postgres.DATABASE_URL}}`)
   - `CORS_ALLOWED_ORIGINS` — domínio público do serviço **frontend** (passo
     seguinte; volte aqui depois de criá-lo)
   - `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` — normalmente **nem precisa
     definir**: `config/settings/production.py` já inclui sozinho o domínio
     que o próprio Railway gera (`RAILWAY_PUBLIC_DOMAIN`, injetado
     automaticamente). Só defina isto à mão se usar um domínio próprio.
   - Opcionais: `MERCADOPAGO_*`, `EVOLUTION_API_*`, `SENTRY_DSN` (ver `.env.example`)
   - `PORT` não precisa ser definida — o Railway injeta e o
     `docker-entrypoint.sh` já lê `$PORT`. O mesmo entrypoint roda `migrate`
     e `collectstatic` a cada deploy, então não é um passo manual à parte.
3. **Frontend** — outro serviço a partir do **mesmo repo**, **Root
   Directory `frontend`** (sem barra na frente). Railway detecta o
   `Dockerfile` dentro de `frontend/`, que builda e sobe `vite preview
   --port $PORT --host 0.0.0.0`. Variável:
   - `VITE_API_BASE_URL=https://<domínio-do-backend>/api/v1` — o Vite embute
     isto em tempo de **build**; o `Dockerfile` do frontend já repassa a
     variável do serviço pro build via `ARG`, então é só configurar no
     painel e fazer deploy — não precisa de passo manual extra. Qualquer
     troca depois exige um novo deploy do frontend, não só reiniciar.
4. Depois que os dois tiverem domínio público, ajuste `CORS_ALLOWED_ORIGINS`
   (backend) e `VITE_API_BASE_URL` (frontend) um apontando pro outro e
   redeploy os dois.
5. Setup inicial (grupos de permissão + primeiro admin) — via [Railway CLI](https://docs.railway.com/guides/cli):
   ```bash
   railway run python manage.py create_default_groups
   railway run python manage.py createsuperuser
   ```

Se algum dos dois serviços não construir automaticamente a partir do
`Dockerfile` certo, confira nas Settings dele: **Root Directory** precisa
bater exatamente com o serviço (`/` no backend, `frontend` no frontend) e,
em Build, o **Builder** deve estar como "Dockerfile" (não "Nixpacks") —
Railway às vezes mantém a escolha antiga de builder de quando o serviço foi
criado, mesmo depois de mudar o Root Directory; force pra Dockerfile
manualmente se isso acontecer.

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

---

Projeto proprietário de uso interno.
