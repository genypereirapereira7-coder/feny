/* Landing da Feny — a rolagem é a linha do tempo.
 *
 * A ideia toda: o vídeo nunca toca sozinho. Ele fica parado e o script diz em
 * que segundo ele deve estar, a partir de quanto da seção do filme já passou
 * pela tela. Topo da seção = começo do vídeo; fim dela = fim do vídeo.
 *
 * Entre o valor que a rolagem pede e o que o vídeo recebe existe uma
 * suavização. Ela importa mais aqui do que pareceria: rolagem de trackpad e
 * de mouse com roda chegam em saltos de tamanhos bem diferentes, e sem
 * amortecer o vídeo andaria liso num aparelho e aos trancos no outro. */

const video = document.getElementById("fundo")
const filme = document.getElementById("filme")
const capitulos = Array.from(document.querySelectorAll(".capitulo"))
const marcas = Array.from(document.querySelectorAll("#marcas li"))
const preenchimento = document.getElementById("preenchimento")
const dica = document.getElementById("dica")
const palco = document.getElementById("capitulos")
const fim = document.getElementById("fim")

/* Fronteiras dos capítulos, em fração do vídeo.
 *
 * Não são números redondos: saem do meio de cada dissolvência da montagem
 * (6,5 s e 13 s de um vídeo de 20,5 s). O texto troca exatamente quando a
 * imagem termina de virar — meio segundo antes ou depois, o olho percebe que
 * as duas coisas são independentes, e é isso que estraga a ilusão.
 *
 * Trocou o vídeo? Refaça esta conta. */
const LIMITES = [6.5 / 20.5, 13 / 20.5]

/* Quanto da distância que falta é percorrida a cada quadro de 60 Hz. Mais
 * alto persegue a rolagem de perto e fica duro; mais baixo escorrega e parece
 * atraso. 0,09 é o ponto em que o vídeo parece pesado, não lento. */
const SUAVIDADE = 0.09

/* Abaixo disto não vale mandar um `currentTime` novo: cada pedido de salto
 * custa decodificação, e diferença menor que meio milésimo do vídeo não muda
 * um pixel na tela. */
const PRECISAO = 0.0005

const movimentoReduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches

let alvo = 0
let atual = 0
let alvoParalaxeX = 0
let alvoParalaxeY = 0
let paralaxeX = 0
let paralaxeY = 0
let capituloAtivo = -1
let noFim = false
let quadro = null
let ultimoInstante = 0

/* ---------------------------------------------------------------- o vídeo */

/* Um caminho só, para qualquer aparelho: o vídeo nasce tocando (`autoplay
 * loop` no HTML) e o script assume o controle assim que ele tocou de verdade.
 *
 * A ordem é o que faz funcionar no iPhone. O Safari não desenha quadro de um
 * vídeo que nunca tocou — posicionar o `currentTime` nele devolve tela preta —
 * e também não carrega nada antes do `play()`. Deixando o atributo tocar
 * primeiro, o decodificador acende sozinho, sem gesto e sem permissão; a
 * partir daí posicionar o vídeo é aceito, e a rolagem passa a comandar o
 * tempo no celular igual ao computador.
 *
 * Por isso o controle é tomado no evento `playing`, e não em `loadedmetadata`:
 * metadados chegam antes do primeiro quadro, e assumir ali deixaria o
 * decodificador apagado — que era exatamente o defeito de antes. O preço é a
 * fração de segundo em que o vídeo aparece tocando, que ninguém estranha num
 * fundo de tela. */
let assumido = false

function assumirControle() {
  if (assumido) return
  assumido = true
  video.loop = false
  video.pause()
  aplicarTempo(alvo)
}

video.addEventListener("playing", assumirControle, { once: true })

/* Se o autoplay for recusado — Modo de Baixo Consumo, aba aberta em segundo
   plano — `playing` não chega e a capa fica na tela. O primeiro toque da
   pessoa vira o gesto que libera: o vídeo toca, `playing` dispara, o controle
   é assumido e a rolagem passa a comandar como em todo mundo. */
function tocar() {
  video.muted = true
  const tentativa = video.play()
  if (tentativa && typeof tentativa.then === "function") {
    tentativa.catch(() => {
      document.addEventListener("touchstart", tocar, { once: true, passive: true })
      document.addEventListener("click", tocar, { once: true })
    })
  }
}

tocar()

function aplicarTempo(fracao) {
  if (!video.duration) return
  video.currentTime = fracao * video.duration
}

/* --------------------------------------------------------------- a rolagem */

/* Quanto da seção do filme já passou, de 0 a 1. O curso é a altura da seção
   menos uma tela: quando o topo dela encosta no topo da janela o valor é 0, e
   quando o fim dela chega ao fundo da janela o valor é 1 — exatamente o
   intervalo em que a tela fica grudada (`position: sticky`). */
function progressoDoFilme() {
  const caixa = filme.getBoundingClientRect()
  const curso = caixa.height - window.innerHeight
  if (curso <= 0) return 0
  return Math.min(Math.max(-caixa.top / curso, 0), 1)
}

function aoRolar() {
  alvo = progressoDoFilme()
  if (alvo > 0.02) dica.classList.add("is-oculta")
  ligarLaco()
}

aoRolar()
window.addEventListener("scroll", aoRolar, { passive: true })
window.addEventListener("resize", aoRolar)

/* Nada de atalho de teclado próprio: a linha do tempo é a rolagem, e rolar
   com Espaço, PageDown e setas já é coisa do navegador. Um atalho nosso por
   cima disso só brigaria com o que a pessoa já sabe fazer. */

/* O ponteiro não manda no tempo do vídeo — manda só no texto, que anda ao
   contrário dele e pouco: 28px no eixo maior. É o bastante pro bloco parecer
   flutuar sobre o vídeo em vez de estar colado nele, e pouco o suficiente
   pra ninguém perceber que está acontecendo, que é o ponto de um efeito de
   profundidade. */
window.addEventListener(
  "pointermove",
  (evento) => {
    if (movimentoReduzido) return
    alvoParalaxeX = (0.5 - evento.clientX / window.innerWidth) * 28
    alvoParalaxeY = (0.5 - evento.clientY / window.innerHeight) * 14
    ligarLaco()
  },
  { passive: true },
)

/* ------------------------------------------------------------------ o laço */

function ligarLaco() {
  if (quadro === null) {
    ultimoInstante = performance.now()
    quadro = requestAnimationFrame(passo)
  }
}

function passo(instante) {
  const decorrido = Math.min(instante - ultimoInstante, 100)
  ultimoInstante = instante

  /* A suavização é corrigida pelo tempo entre quadros, e não aplicada como
     fração fixa. Sem isso, a mesma linha de código roda em velocidades
     diferentes num monitor de 60 Hz e num de 120 Hz — o efeito ficaria duas
     vezes mais rápido na tela melhor, que é o contrário do que se espera. */
  const fator = 1 - Math.pow(1 - SUAVIDADE, decorrido / (1000 / 60))

  atual += (alvo - atual) * fator
  paralaxeX += (alvoParalaxeX - paralaxeX) * fator
  paralaxeY += (alvoParalaxeY - paralaxeY) * fator

  /* Só posiciona depois de o controle ter sido assumido: até lá o vídeo está
     tocando sozinho, e mandar ele pular enquanto toca briga com a própria
     reprodução. */
  if (assumido) aplicarTempo(atual)
  preenchimento.style.transform = `scaleX(${atual})`

  if (!movimentoReduzido) {
    palco.style.transform = `translate3d(${paralaxeX}px, ${paralaxeY}px, 0)`
  }

  trocarCapitulo(atual)

  /* O laço se desliga quando tudo chegou ao destino. Manter um
     `requestAnimationFrame` girando com a página parada gasta bateria de quem
     só deixou a aba aberta — e ele volta sozinho na próxima rolagem. */
  const parado =
    Math.abs(alvo - atual) < PRECISAO &&
    Math.abs(alvoParalaxeX - paralaxeX) < 0.05 &&
    Math.abs(alvoParalaxeY - paralaxeY) < 0.05

  quadro = parado ? null : requestAnimationFrame(passo)
}

/* -------------------------------------------------------------- capítulos */

/* A história tem quatro atos, e o filme tem três cenas: os três primeiros
   vêm do tempo do vídeo, e o quarto (a mensalidade) é a seção de fundo
   sólido que entra quando o filme acaba. Por isso a régua é atualizada por
   dois caminhos — o tempo do vídeo e a chegada da última seção. */
function atualizarRegua(indice) {
  marcas.forEach((marca, i) => marca.classList.toggle("is-ativo", i === indice))
}

function trocarCapitulo(fracao) {
  let indice = 0
  if (fracao > LIMITES[1]) indice = 2
  else if (fracao > LIMITES[0]) indice = 1

  if (indice !== capituloAtivo) {
    capituloAtivo = indice
    capitulos.forEach((capitulo, i) => capitulo.classList.toggle("is-ativo", i === indice))
  }

  if (!noFim) atualizarRegua(indice)
}

trocarCapitulo(0)

/* O ato 04 começa quando a seção da mensalidade toma a maior parte da tela.
   `threshold: 0.35` e não a simples entrada: a seção encosta na tela ainda
   com o último capítulo do filme sendo lido, e trocar a marca ali seria
   trocar antes do assunto mudar. */
if (fim) {
  new IntersectionObserver(
    ([entrada]) => {
      noFim = entrada.isIntersecting
      atualizarRegua(noFim ? 3 : capituloAtivo)
    },
    { threshold: 0.35 },
  ).observe(fim)
}
