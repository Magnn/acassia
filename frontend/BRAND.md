# Sibila — Brand Guidelines

## Origem do nome

**Sibila** vem das *sibyls* da antiguidade — profetisas oraculares (Délfica, Cumana, Frígia, Tiburtina, etc.) que serviam de canal entre o divino e o mundano em templos gregos e romanos. O nome substitui "Cigana" — termo etnicamente carregado pelo qual comunidades Roma têm relação ambivalente. **Sibila** mantém a alma mística do produto sem amarrar a uma identidade étnica específica.

## Tagline

> Atendimento mago, automação real.

A dualidade declarada do produto: **alma esotérica + infraestrutura séria**.

## Personalidade

| É | Não é |
|---|---|
| Considerada, ritualística | Cartoonesca, "divertida" |
| Premium, sofisticada | Cara, distante, fria |
| Mística com peso histórico | Hippie, trippy, neon |
| Profissional B2B | Sterile tech-bro |

Inspiração: Linear (rigor) + Stripe (clareza) + maturidade ritual de uma carta de tarô bem desenhada.

## Logo

Composição: **lua crescente partida por um eixo vertical (axis mundi) + ponto astral**.

- Lua = ciclo, mistério, intuição
- Eixo = canal entre alto e baixo (a função da sibila)
- Ponto astral = alinhamento, visão de longe

Implementação: `frontend/src/components/Logo.tsx`. SVG single-color (currentColor) — herda contexto. Variantes: `default` (com ponto), `outline` (só contorno), `minimal` (sem ponto).

## Wordmark

**Sibila** — em **Fraunces** (modern serif), peso 500, tracking 0.02em.

## Tipografia

| Função | Família | Pesos disponíveis |
|---|---|---|
| **Display** (h1, h2, brand, métricas) | Fraunces | 400, 500, 600 |
| **Body / UI** | Inter | 400, 500, 600, 700, 800 |
| **Mono** (códigos, IDs) | sistema (`ui-monospace`) | — |

Fraunces é serif moderno com personalidade — formas variáveis (opsz), serifas suaves. Inter é o workhorse universal. A combinação dá ritualidade no titulado e legibilidade na UI.

## Paleta — "Noite Considerada"

Núcleo escuro quente (não slate frio) + acentos metálicos restritos.

| Token | Hex | Uso |
|---|---|---|
| `sibila-onyx` | `#0b0817` | Fundo base |
| `sibila-obsidian` | `#14101e` | Cards, surfaces |
| `sibila-veil` | `#1c1828` | Sidebar, hover states |
| `sibila-mist` | `#2a2538` | Bordas suaves |
| `sibila-stone` | `#3a3447` | Bordas duras, divisores |
| `sibila-amethyst` | `#7c6a99` | **Acento primário** — ametista enfumaçada |
| `sibila-amethyst-dim` | `#5a4d72` | Estado pressed/active |
| `sibila-ember` | `#d4a574` | **Acento luxo** — ouro fosco, premium |
| `sibila-ember-deep` | `#a8845c` | Ember pressed |
| `sibila-rose` | `#b46e7c` | Acento quente, highlight intermediário |
| `sibila-sage` | `#7a9b88` | Sucesso (não verde lima) |
| `sibila-crimson` | `#a93c3c` | Erro, perigo (não vermelho HD) |
| `sibila-moonlight` | `#f3eee5` | Texto alto — creme quente |
| `sibila-fog` | `#a8a3b3` | Texto médio |
| `sibila-smoke` | `#6b6677` | Texto baixo, hints, placeholders |

### Quando usar **amethyst** vs **ember**

- **amethyst** — branding cotidiano, navegação ativa, ações primárias, charts secundários
- **ember** — momentos de luxo / destaque excepcional: logo, métricas premium, badges raras, "publicado", revenue

Não usar os dois com a mesma intensidade — ember é tempero, não tinta de fundo.

## Tokens de sombra

- `shadow-glow-amethyst` — halo difuso primário (botões em foco, brand mark)
- `shadow-glow-ember` — halo dourado (logo no header, badges de status premium)
- `shadow-inset-veil` — borda interna sutil (cards, panels) — dá profundidade a superfícies escuras

## Espaçamento e raios

- Border radius padrão: `rounded-lg` (8px) para cards, `rounded-md` (6px) para botões secundários, `rounded` (4px) para chips/badges
- Padding interno de cards: `p-5` (20px)
- Gap entre seções: `gap-3` (12px) ou `mb-8` entre blocos maiores

## Migração de tokens

Os tokens legados `cigana-bg`, `cigana-surface`, `cigana-border`, `cigana-purple` continuam definidos em `tailwind.config.ts`, **agora apontando para os valores Sibila correspondentes**. Código antigo segue funcionando; código novo deve usar `sibila-*` direto.

| Legado | Novo equivalente |
|---|---|
| `cigana-bg` | `sibila-onyx` |
| `cigana-surface` | `sibila-obsidian` |
| `cigana-border` | `sibila-mist` |
| `cigana-purple` | `sibila-amethyst` |

## Voice & tone (copy do produto)

| Em vez de | Prefira |
|---|---|
| "Carregando..." | "Consultando os astros…" (em telas de loading principais; sutilezas só nos lugares certos) |
| "Erro: undefined" | "Não consegui completar essa leitura. Tenta de novo em um momento." |
| "Save" / "Submit" | "Salvar", "Publicar", "Selar" |
| "User" / "Profile" | "Atendente", "Persona" |
| "Funnel" | "Funil" (já está em PT) ou "Caminho" |

Manter raridade — não exagerar nos termos místicos. **Um por tela** é mais elegante que cinco.

## Implementação

- `tailwind.config.ts` — tokens
- `frontend/src/components/Logo.tsx` — marca SVG + Wordmark
- `frontend/src/components/Layout.tsx` — sidebar + header globais aplicando a paleta
- `frontend/index.html` — carrega Fraunces + Inter via Google Fonts

Ver também: pt-br nas labels da nav, agrupamento por seção (Painel / Oráculo / Configuração).
