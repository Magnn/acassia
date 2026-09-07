# Manifest de assets do baralho de Marselha

> 79 imagens necessárias pro template **Tiragem Express**. Este doc é o guia pra preparar e subir os assets pro Supabase Storage (ver [ADR_004](adr/ADR_004_supabase_storage.md)).

---

## O que precisa estar no Supabase Storage

**Bucket:** `templates-public` (público — read sem auth)
**Pasta:** `marselha/`
**Total:** 79 arquivos `.jpg`

| Categoria | Qtd | Slugs |
|---|---|---|
| Baralho fechado | 1 | `baralho_fechado` |
| Arcanos Maiores (0-21) | 22 | `o_louco`, `o_mago`, `a_sacerdotisa`, ..., `o_mundo` |
| Copas | 14 | `as_de_copas`, `dois_de_copas`, ..., `rei_de_copas` |
| Espadas | 14 | `as_de_espadas`, ..., `rei_de_espadas` |
| Ouros | 14 | `as_de_ouros`, ..., `rei_de_ouros` |
| Bastões | 14 | `as_de_bastoes`, ..., `rei_de_bastoes` |

Pra ver a lista completa exata:

```bash
python scripts/upload_marselha_storage.py --list
```

A nomenclatura dos slugs é definida em [`flows/tarot/cartas.py`](../flows/tarot/cartas.py) — fonte da verdade.

URL pública resultante por carta:
```
https://{project}.supabase.co/storage/v1/object/public/templates-public/marselha/{slug}.jpg
```

---

## De onde tirar as 79 imagens?

3 opções, em ordem de qualidade percebida:

### Opção A — Comprar baralho + fotografar (recomendado pra produção)

Comprar um baralho ilustrado de Marselha (ex: **Tarot de Marselha de Camoin-Jodorowsky**, ou **Marselha Conver**, ~R$ 100-300), fotografar cada carta com fundo neutro e luz uniforme.

- **Custo:** R$ 200-500 + 2-3 horas de fotografia
- **Vantagem:** identidade visual única, profissional, branding seu
- **Desvantagem:** trabalho manual; precisa de câmera decente

### Opção B — Wikimedia Commons (CC0 / domínio público)

Imagens do **Tarot de Marseille (1672)** estão em [domínio público](https://commons.wikimedia.org/wiki/Category:Tarot_de_Marseille_de_Conver_1761) no Wikimedia.

- **Custo:** R$ 0
- **Vantagem:** legal, rápido
- **Desvantagem:** visual antigo, qualidade variada por carta, não é diferencial

### Opção C — Gerar com IA (Midjourney / DALL-E / Gemini)

Prompts consistentes geram 78 cartas com estilo único.

- **Custo:** R$ 50-100 (tokens / créditos)
- **Vantagem:** identidade total, ágil
- **Desvantagem:** consistência inter-cartas é difícil; iteração consome tempo
- **Dica:** definir um único prompt-mestre com paleta + estilo + composição, e variar só por carta (ex: "um homem com 7 espadas atrás dele, estilo de gravura medieval francesa, mesma paleta das demais")

### Opção mista (sugerida pro MVP)

Para os primeiros betas:
- **Wikimedia** pras 78 cartas (rapidez)
- **Foto custom** pra `baralho_fechado.jpg` (com sua marca, é a primeira imagem que o lead vê)
- Conforme tração, substituir gradualmente por opção A ou C

---

## Convenção de nomeação dos arquivos

Os arquivos na sua pasta local **DEVEM** ter exatamente os slugs esperados, em lowercase, sem acentos, terminando em `.jpg`.

Exemplos válidos:
- ✅ `o_louco.jpg`
- ✅ `a_torre.jpg`
- ✅ `dez_de_espadas.jpg`
- ✅ `rei_de_bastoes.jpg`
- ✅ `baralho_fechado.jpg`

Inválidos (vão dar mismatch no upload):
- ❌ `O Louco.jpg` (espaço, maiúscula)
- ❌ `a_torre.jpeg` (extensão errada)
- ❌ `rei_de_bastões.jpg` (acento)
- ❌ `baralho-fechado.jpg` (hífen em vez de underscore)

---

## Como subir (passo a passo)

### Pré-requisitos

1. Bucket `templates-public` criado no Supabase e marcado como **público** (Settings → Storage → Edit bucket → Public)
2. `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` no ambiente
   - Service role key: Settings → API → `service_role` (chave secreta — **nunca** commit)

### Passo 1 — Validar a pasta local

```bash
python scripts/upload_marselha_storage.py /caminho/imagens --dry-run
```

Deve mostrar `encontrados: 79/79`. Se aparecer "AUSENTES", complete antes de subir.

### Passo 2 — Subir

```bash
SUPABASE_URL=https://abc.supabase.co \
SUPABASE_SERVICE_ROLE_KEY=eyJhbG... \
python scripts/upload_marselha_storage.py /caminho/imagens
```

Espere a saída `--- RESUMO --- sucessos=79 falhas=0`.

### Passo 3 — Smoke test

```python
from flows.tarot.cartas import sortear_3_cartas, url_imagem

BASE = "https://abc.supabase.co/storage/v1/object/public/templates-public"
for c in sortear_3_cartas(seed=0):
    print(c.nome, url_imagem(c, BASE))
```

Cole as URLs no navegador — devem abrir as imagens diretamente.

### Passo 4 — Marcar G2 como concluído

Em [GAP_ENGINE_VS_CIGANA_TAROT.md](GAP_ENGINE_VS_CIGANA_TAROT.md), trocar `| G2 |` por `| ✅ G2 |`.

---

## Trocar imagens depois (sem downtime)

`scripts/upload_marselha_storage.py` usa `x-upsert: true`, então rodar de novo **sobrescreve** as existentes. Como a URL pública é cacheada por CDN do Supabase, mudanças podem demorar alguns minutos pra propagar — não é instantâneo.

Pra forçar invalidação imediata: trocar o nome (ex: `a_torre_v2.jpg`) e atualizar o slug em `flows/tarot/cartas.py`. Isso quebra cache imediatamente em troca de 1 deploy.

---

## Considerações de licenciamento

- **Wikimedia:** verificar a licença de cada imagem individual. Maioria é PD (1761 está em domínio público), mas algumas digitalizações modernas têm CC-BY-SA — créditos exigidos
- **Compras:** baralhos físicos têm direito autoral nas ilustrações. Fotografar pra uso interno do produto é zona cinza; consultar advogado se for revender o baralho como produto físico
- **IA:** termos de uso variam — Midjourney comercial requer plano pago; DALL-E permite uso comercial; Gemini idem. Sempre conferir
