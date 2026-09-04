# Segurança — Feny

Referência viva do checklist de segurança da ARCHITECTURE.md §13. Atualizar
sempre que algo aqui mudar de status — não deixar este documento ficar
desatualizado em relação ao código.

## Checklist de produção (§13)

| Item | Status | Onde |
|---|---|---|
| `DEBUG = False`, `ALLOWED_HOSTS` restrito, `CSRF_TRUSTED_ORIGINS` explícito | ✅ | `config/settings/production.py` |
| `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY` | ✅ | `config/settings/production.py` |
| `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS = "DENY"` | ✅ | `config/settings/production.py` |
| 2FA obrigatório para `ADMIN`/`MANAGER`/`FINANCE` | ✅ | `apps/users/two_factor.py`, `apps/users/authentication.py` |
| Rate limiting no login e no webhook do Mercado Pago | ✅ | `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`, `LoginView`, `MercadoPagoWebhookView` |
| Rate limiting em recuperação de senha | N/A | Recuperação de senha nunca foi construída em nenhuma fase — não existe endpoint pra limitar |
| Segredos só via variável de ambiente | ✅ | `.env` (nunca commitado), `.env.example` sim |
| Upload: tamanho, extensão, magic number, nome nunca confiado do cliente | ✅ | `apps/documents/validators.py` |
| Logs nunca com senha/token/CPF-CNPJ cru/payload financeiro completo | ✅ | ver "Logging" abaixo |
| Refresh token rotacionado não pode ser reusado | ✅ | `SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"]` |

## 2FA (TOTP)

Obrigatório para `ADMIN`, `MANAGER` e `FINANCE` (`apps/users/two_factor.py::PAPEIS_COM_2FA_OBRIGATORIO`).

- **Login**: `POST /api/v1/auth/token/` com `username`/`password` (e `otp_code` se
  2FA já estiver ativo, na mesma chamada).
- Se o papel exige 2FA e ainda não foi configurado, o login funciona mas o
  token devolvido só abre `/users/me/`, `/auth/2fa/setup/`, `/auth/2fa/confirm/`
  e `/auth/token/refresh/` — todo o resto responde 401 até a configuração
  ser concluída (`apps/users/authentication.py`).
- **Configurar**: `POST /api/v1/auth/2fa/setup/` (autenticado) devolve
  `secret` + `otpauth_url` pro QR code. `POST /api/v1/auth/2fa/confirm/` com
  `{"code": "123456"}` do app autenticador ativa de verdade.
- **Perdeu o dispositivo**: só um `ADMIN` resolve, via
  `POST /api/v1/users/{id}/reset-2fa/` — zera o segredo, a pessoa configura
  de novo no próximo login.

**Limitação conhecida**: a trava de 2FA cobre a API (`/api/v1/...`), que é o
que o frontend usa. O login do **Django admin** (`/admin/`) é o mecanismo
padrão do Django — sessão + usuário/senha — e não passa por
`TwoFactorAwareJWTAuthentication` nenhuma, então um `ADMIN`/`MANAGER`/`FINANCE`
tecnicamente consegue entrar no admin sem 2FA. Isso não é um descuido
silencioso: é um gap real, registrado aqui de propósito. Fechar isso exigiria
uma segunda trava (`AdminSite` customizado ou middleware específico pro
`/admin/`), fora do escopo desta fase — quem usar `/admin/` como interface de
verdade (não só um painel de leitura ocasional) deveria tratar isso como
próximo passo de segurança.

## Rate limiting

Configurado em `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`
(`config/settings/base.py`):

- `login`: 10/min — `POST /api/v1/auth/token/`
- `mercadopago-webhook`: 60/min — `POST /api/webhooks/mercadopago/` (por IP,
  já que não há usuário autenticado nesse endpoint)

## Upload de arquivos

`apps/documents/validators.py`: limite de 20MB, whitelist de extensão, nome
do arquivo nunca confiado (storage usa UUID), e checagem do magic number
(bytes reais do arquivo) para `.pdf/.jpg/.jpeg/.png/.docx/.xlsx/.doc/.xls` —
`.txt` fica de fora da checagem de conteúdo de propósito, por não ter uma
assinatura binária confiável.

Limitação conhecida: `.docx`/`.xlsx` compartilham a mesma assinatura (ambos
são ZIP por dentro) — a checagem não abre o ZIP pra confirmar qual dos dois é
de verdade.

## Logging

`LOGGING` (`config/settings/base.py`) nunca loga corpo de requisição por
padrão — só o logger `django.request` do próprio Django (nível, método,
path). Nenhum código da aplicação loga `password`, tokens JWT,
`two_factor_secret` ou o payload bruto de webhook do Mercado Pago
(`Payment.raw_payload` é persistido no banco pra auditoria/conciliação —
dado em repouso, não em log de aplicação).

## Backup e restauração

`scripts/backup_db.sh` — `pg_dump` em formato custom (`-Fc`), lê
`DATABASE_URL` do ambiente. `scripts/restore_db.sh` — restaura num banco
**novo** (nunca sobrescreve o banco de origem), pra provar que o processo de
restauração funciona de verdade, não só que existe um arquivo de backup em
algum lugar.

```bash
./scripts/backup_db.sh backup.dump
./scripts/restore_db.sh backup.dump feny_restore_test   # teste periódico
```

Em produção: agendar `backup_db.sh` por cron, reter um número definido de
gerações, e rodar `restore_db.sh` periodicamente contra um banco de teste
(não só confiar que os arquivos existem). Storage de documentos
(`apps/documents`): backup fica a cargo do provedor de storage externo
(S3-compatível, §14) quando produção migrar pra ele — versionamento/réplica
do lado do provedor, não algo que este repositório precisa implementar.

## Observabilidade

- `GET /health/` confere a conexão com o banco de verdade (`SELECT 1`), não
  só se o processo Django está de pé — um deploy com banco fora do ar
  responde 503, não 200.
- Sentry (rastreamento de erro) é opcional, ligado só se
  `SENTRY_DSN` estiver configurado em produção (`config/settings/production.py`)
  — sem DSN configurado, roda normalmente sem ele.

## Reportar um problema de segurança

Plataforma de uso interno da Feny — reportar diretamente ao time técnico,
não há processo público de disclosure.
