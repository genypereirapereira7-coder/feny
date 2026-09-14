/* Página "Começar um projeto".
 *
 * Três coisas: o formulário que vira lead no sistema, as dúvidas abrindo com
 * altura animada e a revelação das seções ao rolar. Sem framework — a página
 * é uma só e nada aqui precisa de estado compartilhado. */

const movimentoReduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches

/* ==========================================================================
   Formulário → lead no sistema
   ========================================================================== */

/* Em produção a API é do mesmo domínio (o Django serve esta página). Em
   desenvolvimento a landing roda num servidor estático e a API noutro, então
   o endereço precisa ser explícito — e é por isso que `localhost:4200` está
   em CORS_ALLOWED_ORIGINS no backend. */
const API = location.port === "4200" ? "http://localhost:8001/api/v1" : "/api/v1"

const LIMITE_MENSAGEM = 2000

const form = document.getElementById("form-contato")
const aviso = document.getElementById("aviso")
const botaoEnviar = document.getElementById("enviar")

function somenteDigitos(valor) {
  return valor.replace(/\D/g, "")
}

/* Tira o +55 antes de contar os dígitos — número colado do WhatsApp vem com o
   código do país, que não faz parte do telefone. Mesma normalização de
   `apps/leads/validators.py::normalizar_telefone`. */
function normalizarTelefone(valor) {
  const digitos = somenteDigitos(valor)
  if ((digitos.length === 12 || digitos.length === 13) && digitos.startsWith("55")) {
    return digitos.slice(2)
  }
  return digitos
}

function formatarTelefone(valor) {
  const d = normalizarTelefone(valor).slice(0, 11)
  if (d.length <= 2) return d
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
}

function telefoneValido(valor) {
  const digitos = normalizarTelefone(valor)
  if (digitos.length !== 10 && digitos.length !== 11) return false

  const ddd = digitos.slice(0, 2)
  if (ddd[0] === "0" || ddd[1] === "0") return false

  const numero = digitos.slice(2)
  // Celular ganhou o nono dígito em 2016; fixo nunca começa com 0 ou 1.
  if (numero.length === 9 && numero[0] !== "9") return false
  if (numero.length === 8 && (numero[0] === "0" || numero[0] === "1")) return false
  return true
}

/* Checagem de e-mail intencionalmente frouxa: "tem algo, arroba, algo, ponto,
   algo". Regex de RFC completa recusa endereço válido de vez em quando, e o
   erro de digitação de verdade ("maria@gmail") esta pega igual. Quem decide
   de fato é o `EmailField` do Django. */
function emailValido(valor) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(valor)
}

/* Espelha, campo a campo, `apps/leads/api/serializers.py::PublicLeadSerializer`.
   As duas camadas existem de propósito e não são redundantes: esta é
   conveniência — o visitante vê o erro embaixo do campo sem esperar
   requisição; a do backend é o portão de verdade, porque o endpoint é público
   e qualquer um pode postar direto nele sem passar por esta tela.
   Quando uma regra mudar, mude nos dois lugares: o backend é quem manda. */
function validar(dados) {
  const erros = {}

  const nome = dados.name.trim()
  if (!nome) erros.name = "Diga como podemos te chamar."
  else if (nome.length < 2 || !/\p{L}/u.test(nome)) erros.name = "Informe seu nome."

  const email = dados.email.trim()
  if (!email) erros.email = "Precisamos de um e-mail pra te responder."
  else if (!emailValido(email)) erros.email = "E-mail inválido — confira se não faltou uma letra."

  if (!dados.phone.trim()) erros.phone = "Informe um WhatsApp com DDD."
  else if (!telefoneValido(dados.phone)) erros.phone = "Telefone inválido — informe DDD + número."

  if (!dados.service_type) erros.service_type = "Escolha o que você precisa."

  const mensagem = dados.message.trim()
  if (!mensagem) erros.message = "Conte o que você precisa."
  else if (mensagem.length < 10) erros.message = "Conte um pouco mais — pelo menos 10 caracteres."
  else if (mensagem.length > LIMITE_MENSAGEM) erros.message = `Resuma em até ${LIMITE_MENSAGEM} caracteres.`

  return erros
}

function mostrarErros(erros) {
  form.querySelectorAll(".campo").forEach((campo) => campo.classList.remove("is-invalido"))
  form.querySelectorAll(".erro").forEach((span) => (span.textContent = ""))

  Object.entries(erros).forEach(([campo, mensagem]) => {
    const alvoErro = document.getElementById(`erro-${campo}`)
    const entrada = document.getElementById(campo)
    if (alvoErro) alvoErro.textContent = mensagem
    if (entrada) {
      entrada.closest(".campo")?.classList.add("is-invalido")
      // `aria-invalid` é o que o leitor de tela usa pra anunciar "inválido" —
      // a borda vermelha sozinha não diz nada pra quem não a vê.
      entrada.setAttribute("aria-invalid", "true")
    }
  })
}

const telefone = document.getElementById("phone")
telefone.addEventListener("input", () => {
  telefone.value = formatarTelefone(telefone.value)
})

// O erro some assim que a pessoa mexe no campo: deixar o vermelho aceso
// enquanto ela corrige passa a impressão de que ainda está errado.
form.addEventListener("input", (evento) => {
  const campo = evento.target.closest(".campo")
  if (!campo) return
  campo.classList.remove("is-invalido")
  evento.target.removeAttribute("aria-invalid")
  const span = campo.querySelector(".erro")
  if (span) span.textContent = ""
})

form.addEventListener("submit", async (evento) => {
  evento.preventDefault()
  aviso.textContent = ""
  aviso.className = "aviso"

  const dados = {
    name: form.name.value,
    company: form.company.value,
    email: form.email.value,
    phone: form.phone.value,
    service_type: form.service_type.value,
    budget_range: form.budget_range.value,
    message: form.message.value,
    website: form.website.value,
  }

  const erros = validar(dados)
  if (Object.keys(erros).length > 0) {
    mostrarErros(erros)
    // Leva a tela até o primeiro campo com problema — num formulário desta
    // altura, a mensagem pode ficar fora da vista de quem apertou enviar.
    document.getElementById(Object.keys(erros)[0])?.focus()
    return
  }

  mostrarErros({})
  botaoEnviar.disabled = true
  botaoEnviar.textContent = "Enviando…"

  try {
    const resposta = await fetch(`${API}/public/contact/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...dados, phone: normalizarTelefone(dados.phone) }),
    })

    if (resposta.ok) {
      form.reset()
      aviso.className = "aviso is-ok"
      aviso.textContent = "Recebemos seu contato. A Feny responde em até 1 dia útil."
      return
    }

    if (resposta.status === 429) {
      aviso.className = "aviso is-erro"
      aviso.textContent = "Muitas tentativas seguidas. Espere um minuto e envie de novo."
      return
    }

    // O backend devolve erro por campo, no mesmo nome que o formulário usa —
    // então dá pra jogar direto embaixo do campo certo em vez de mostrar um
    // aviso genérico que não diz o que corrigir.
    const corpo = await resposta.json().catch(() => ({}))
    const porCampo = {}
    Object.entries(corpo).forEach(([campo, mensagens]) => {
      if (document.getElementById(campo)) {
        porCampo[campo] = Array.isArray(mensagens) ? mensagens[0] : String(mensagens)
      }
    })

    if (Object.keys(porCampo).length > 0) {
      mostrarErros(porCampo)
      document.getElementById(Object.keys(porCampo)[0])?.focus()
    } else {
      aviso.className = "aviso is-erro"
      aviso.textContent = "Não foi possível enviar agora. Tente de novo ou chame no WhatsApp."
    }
  } catch {
    aviso.className = "aviso is-erro"
    aviso.textContent = "Sem conexão com o servidor. Tente de novo ou chame no WhatsApp."
  } finally {
    botaoEnviar.disabled = false
    botaoEnviar.textContent = "Enviar e receber retorno"
  }
})

/* ==========================================================================
   Dúvidas: `<details>` nativo com altura animada
   ========================================================================== */

/* O `<details>` continua sendo o elemento de verdade — teclado, leitor de
   tela e o Ctrl+F do navegador vêm de graça, e abre mesmo se este script
   falhar. O que o nativo não faz é animar altura: ele mostra e esconde de uma
   vez. Então interceptamos o clique, animamos, e só depois deixamos o
   navegador mudar o estado. */
document.querySelectorAll(".duvida").forEach((duvida) => {
  const resumo = duvida.querySelector("summary")
  const corpo = duvida.querySelector(".duvida__corpo")

  resumo.addEventListener("click", (evento) => {
    if (movimentoReduzido) return

    evento.preventDefault()

    if (duvida.open) {
      const animacao = corpo.animate([{ height: `${corpo.scrollHeight}px` }, { height: "0px" }], {
        duration: 280,
        easing: "cubic-bezier(0.16, 1, 0.3, 1)",
      })
      animacao.onfinish = () => {
        duvida.open = false
        corpo.style.height = ""
      }
    } else {
      duvida.open = true
      corpo.animate([{ height: "0px" }, { height: `${corpo.scrollHeight}px` }], {
        duration: 320,
        easing: "cubic-bezier(0.16, 1, 0.3, 1)",
      })
    }
  })
})

/* ==========================================================================
   Revelação das seções ao rolar
   ========================================================================== */

/* Uma vez só por elemento: reanimar a cada ida e volta da rolagem deixa a
   página inquieta e cobra processamento pelo resto da visita. */
const observador = new IntersectionObserver(
  (entradas, obs) => {
    entradas.forEach((entrada) => {
      if (!entrada.isIntersecting) return
      entrada.target.classList.add("is-visivel")
      obs.unobserve(entrada.target)
    })
  },
  { rootMargin: "0px 0px -10% 0px" },
)

document.querySelectorAll("[data-revela]").forEach((elemento) => {
  /* O atraso em cascata vem da posição do elemento dentro do próprio pai, não
     da página inteira: senão o último bloco da última seção esperaria dois
     segundos pra aparecer. */
  const irmaos = Array.from(elemento.parentElement.children).indexOf(elemento)
  elemento.style.transitionDelay = `${Math.min(irmaos, 6) * 60}ms`
  observador.observe(elemento)
})

document.getElementById("ano").textContent = String(new Date().getFullYear())
