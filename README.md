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

🏗️ **Fase de arquitetura.** Nenhum código de aplicação ainda.

A arquitetura técnica completa está em **[ARCHITECTURE.md](ARCHITECTURE.md)** — domínios, modelos de dados, máquinas de estado, regras de negócio (30/70, comissão, idempotência), integrações externas, segurança e roadmap de implementação por fases.

## Stack planejada

Python · Django · Django REST Framework · PostgreSQL · Monólito modular

## Roadmap

- [ ] **Fase 1** — Fundação (Django, PostgreSQL, Custom User, autenticação, RBAC base, Docker)
- [ ] **Fase 2** — Clientes
- [ ] **Fase 3** — Comercial (orçamentos e aprovação)
- [ ] **Fase 4** — Projetos e máquina de estado
- [ ] **Fase 5** — Financeiro (interno, sem integração externa ainda)
- [ ] **Fase 6** — Mercado Pago (cobrança, webhooks, idempotência)
- [ ] **Fase 7** — Evolution API (WhatsApp)
- [ ] **Fase 8** — Cobrança recorrente
- [ ] **Fase 9** — Dashboard e relatórios
- [ ] **Fase 10** — Hardening (segurança, performance, backup, observabilidade)

---

Projeto proprietário de uso interno.
