# Spec Acássia 360° — Frente 3: Inbox-as-product + Funnel Intelligence

> Source-of-truth versionado. Status: 📝 spec aprovada, 🚧 implementação não iniciada.
> Última atualização: 2026-04-29

## Inventário (mapa completo)

| #    | Feature                                       | Crítico? | Sprint |
|------|-----------------------------------------------|----------|--------|
| 3.1  | Inbox 3-painel layout                         | 🔴 sim   | A      |
| 3.2  | Lead card na fila (avatar/score/preview)      | 🔴 sim   | A      |
| 3.3  | Filtros de fila                               | 🔴 sim   | A      |
| 3.4  | Sort de fila                                  | 🔴 sim   | A      |
| 3.5  | Busca rápida na fila                          | 🔴 sim   | A      |
| 3.6  | Atalhos de teclado completos                  | 🟡 alto  | A      |
| 3.7  | Conversa: bubbles + áudio inline              | 🔴 sim   | A      |
| 3.8  | Conversa: imagens expandíveis + carousel      | 🔴 sim   | A      |
| 3.9  | Conversa: video player                        | 🟡 alto  | B      |
| 3.10 | Conversa: documentos (PDF preview)            | 🟡 alto  | B      |
| 3.11 | Compose box com toolbar                       | 🔴 sim   | A      |
| 3.12 | Templates rápidos no compose                  | 🔴 sim   | A      |
| 3.13 | Sugestão IA "responder por mim"               | 🟡 alto  | B      |
| 3.14 | Gravação de áudio inline (mic)                | 🟡 alto  | B      |
| 3.15 | Anexar mídia                                  | 🔴 sim   | A      |
| 3.16 | Reactions (emoji em mensagens)                | 🟢 médio | C      |
| 3.17 | Pin message no histórico                      | 🟢 médio | C      |
| 3.18 | Painel contexto: dados do lead                | 🔴 sim   | A      |
| 3.19 | Painel contexto: jornada no fluxo             | 🔴 sim   | A      |
| 3.20 | Painel contexto: gráfico de sentimento        | 🟡 alto  | B      |
| 3.21 | Painel contexto: IA sugere próxima ação       | 🟡 alto  | B      |
| 3.22 | Painel contexto: histórico de compra          | 🟡 alto  | B      |
| 3.23 | Painel contexto: notas livres                 | 🟢 médio | C      |
| 3.24 | Lead scoring engine                           | 🔴 sim   | B      |
| 3.25 | Lead scoring banda visual (hot/warm/cold)     | 🔴 sim   | B      |
| 3.26 | Funnel waterfall por fluxo                    | 🔴 sim   | B      |
| 3.27 | Drop heatmap nos nós do funil                 | 🟡 alto  | B      |
| 3.28 | A/B test em nó (criação)                      | 🟡 alto  | C      |
| 3.29 | A/B test winner picking auto                  | 🟡 alto  | C      |
| 3.30 | Heatmap de horário                            | 🟡 alto  | B      |
| 3.31 | Best/worst message analysis                   | 🟡 alto  | C      |
| 3.32 | Recovery suggestions visual                   | 🟡 alto  | C      |
| 3.33 | LTV por canal/UTM                             | 🟡 alto  | C      |
| 3.34 | UTM tracking pipeline                         | 🟡 alto  | C      |
| 3.35 | Lead source attribution                       | 🟢 médio | C      |
| 3.36 | Lead tags + segmentação                       | 🟡 alto  | B      |
| 3.37 | Bulk actions em leads                         | 🟡 alto  | B      |
| 3.38 | Atribuição de lead a atendente                | 🟡 alto  | B      |
| 3.39 | SLA tracker (tempo de resposta)               | 🟢 médio | C      |
| 3.40 | Auto-snooze de leads                          | 🟢 médio | C      |
| 3.41 | Macros (sequência de ações)                   | 🟢 médio | D      |
| 3.42 | Inbox notifications (sino + sound)            | 🔴 sim   | A      |
| 3.43 | Conversation routing rules                    | 🟢 médio | D      |
| 3.44 | Conversation handoff (bot → humano)           | 🟡 alto  | B      |
| 3.45 | CSAT post-conversa                            | 🟢 médio | D      |

---

## 3.1 Inbox 3-painel layout

### Por quê
Hoje `/leads` é tela linear de mensagens. Vai virar **central de comando** — fila + conversa + contexto numa tela só.

### User Story
**Como** atendente/tarólogo, **quero** uma tela única com fila de leads à esquerda, conversa no centro e contexto do lead à direita, **pra** atender múltiplos leads sem trocar de aba.

### Layout (ASCII mockup)
```
┌─────────────┬─────────────────────────────────┬───────────────┐
│ Fila (280)  │ Conversa: Maria Silva           │ Contexto      │
├─────────────┼─────────────────────────────────┼───────────────┤
│ 🔍 buscar   │ ┌──────────────────────────────┐│ Lead          │
│ [filters ▾] │ │  bubbles chat                ││ ┌───────────┐ │
│             │ │                              ││ │ avatar    │ │
│ ◉ Maria 🔥  │ │  texto bot                   ││ │ Maria     │ │
│   "preciso" │ │            texto user (dir)  ││ │ ♉ Touro   │ │
│   há 2min   │ │                              ││ │ 38 anos   │ │
│ ─────────── │ │  audio bot ▶━━━━━━━━ 0:23   ││ │ SP        │ │
│ ○ João 🟡   │ │            imagem user [x]   ││ └───────────┘ │
│   "obrigado"│ │                              ││               │
│   há 1h     │ │                              ││ Jornada       │
│ ─────────── │ │                              ││ Nó: oferta_3  │
│ ○ Ana ❄️    │ │                              ││ Há 12min      │
│             │ ├──────────────────────────────┤│               │
│  ↓↓ scroll  │ │ [🤖] [⚡] [📎] [🎤] [_____] [▶]││ Sentimento   │
│             │ │      compose                 ││ ●●●○○ pos    │
│             │ └──────────────────────────────┘│               │
│             │                                  │ IA sugere    │
│             │                                  │ "fala em..."  │
└─────────────┴─────────────────────────────────┴───────────────┘
   280px               flex                          320px
```

### Comportamentos
- **Coluna A (fila)**: scroll virtual, atualiza realtime via SSE/WS
- **Coluna B (conversa)**: scroll bottom-pinned (auto-scroll em msg nova se já estava no fundo), preserva scroll se user estava lendo histórico
- **Coluna C (contexto)**: collapse-to-icons em < 1280px, drawer em < 768px
- **Mobile** (< 768px): vira stack — só fila, click → vai pra tela conversa, swipe → contexto

### Estados de erro
- API fila falha: skeleton + retry
- WebSocket disconnect: banner amarelo "reconectando..." + fallback polling 5s
- Conversa não carrega: empty + retry

### Permissões
- Atendente vê apenas leads atribuídos a si (config) ou todos (config workspace)
- Viewer vê tudo read-only (sem compose)

### Métricas
- `inbox.opened`
- `inbox.lead_clicked` {position, score_band}
- `inbox.column_collapsed` {column}

### Rollout
1. Layout 3-painel desktop
2. Mobile responsivo
3. Realtime updates

---

## 3.2 Lead card na fila

### UX
```
┌──────────────────────────────────────┐
│ ◉ 🔥 Maria Silva               2min  │
│   📩 "preciso de uma tiragem urgent..│
│   ✉ funil_principal · #amor          │
│   👤 João (atribuído)                │
└──────────────────────────────────────┘
```

### Elementos
- Bolinha não-lida (◉) ou lida (○)
- Score badge: 🔥 hot / 🟡 warm / ❄️ cold
- Nome (truncado max 20 chars)
- Tempo desde última msg (relativo: 2min, 1h, ontem, 3d, +30d)
- Preview última msg (truncado 60 chars, prefixed 📩 inbound ou 📤 outbound)
- Linha 3: badges — fluxo atual, tags
- Linha 4: atendente atribuído (se houver)

### Estados
- Hover: bg lift + botões inline (atribuir, snooze, fechar)
- Selected: bg accent + border left amethyst
- Unread: nome bold + bolinha cheia
- Snoozed: opacity 50% + ícone 💤
- Closed: opacity 30%, em filtro separado

### Densidade
- Default 72px altura/linha
- Toggle "compact" → 48px (sem preview, só nome+score)

### Métricas
- `inbox.card_hover` (sample)

---

## 3.3 Filtros de fila

### Filtros disponíveis (chip multiselect)
- **Status**: aberta, fechada, snoozed, todos
- **Score**: 🔥, 🟡, ❄️
- **Atribuição**: a mim, a outra pessoa, sem atribuição
- **Fluxo**: dropdown com fluxos do tenant
- **Tags**: multiselect autocomplete
- **Período último contato**: < 1h, < 24h, < 7d, > 7d
- **Tem oferta clicada**: yes/no
- **Pagamento pendente**: yes/no
- **Canal**: WhatsApp, Instagram DM, etc

### UX
- Chips horizontais topo da coluna A
- "Mais filtros" → drawer com campos avançados (data range, value range, etc)
- "Limpar tudo" se há filtros ativos
- Combo de filtros = AND
- Multiselect dentro do mesmo filtro = OR

### Saved filters
- Botão "salvar como vista" → nomeia → aparece na sidebar
- Vistas pessoais e do workspace (admin compartilha)

### Data Model
```sql
CREATE TABLE inbox_saved_views (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  tenant_id VARCHAR(64),
  name VARCHAR(100),
  filters JSONB,
  is_workspace_view BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### API
```
GET /api/leads
  ?status=open&score=hot&assigned=me&flow=funil_x&tags=amor,urgente
  &since=2026-04-01&search=maria
  &sort=last_message:desc
  &cursor=&limit=50
  → {leads, cursor_next}
```

### Métricas
- `inbox.filter_applied` {filter_key, value}
- `inbox.saved_view_created`

---

## 3.4 Sort de fila

### Opções
- **Recência** (default): última msg desc
- **Score**: hot → cold
- **Urgência**: composto de score × tempo desde resposta
- **Alfabético**: nome A→Z
- **Valor potencial**: R$ estimado desc (Pro+)
- **Custom**: arrastar e ordenar manualmente (Enterprise)

### UX
- Dropdown topo "Ordenar: Recência ▾"
- Persiste em localStorage por user

---

## 3.5 Busca rápida na fila

### UX
- Input top da coluna A com 🔍
- Atalho `/` foca o campo
- Search local (já carregados) + remote (debounce 300ms) acima

### Search fields
- Nome, telefone, email, conteúdo última msg, tags

### Highlights
- Match dentro do card destaca em amarelo

### API
```
GET /api/leads/search?q=maria&limit=20 → {leads}
```

### Edge cases
- Query vazia: limpa filtro de busca
- Query só números: assume telefone (busca exata)
- Query > 200 chars: trunca

---

## 3.6 Atalhos de teclado

### Lista completa
| Atalho       | Ação                                       |
|--------------|--------------------------------------------|
| `J / K`      | Próximo / anterior lead                    |
| `Enter`      | Abre conversa                              |
| `Esc`        | Volta pra fila / fecha modal               |
| `R`          | Reply (foca compose)                       |
| `1` ... `9`  | Manda quick template 1..9                  |
| `Cmd+Enter`  | Envia mensagem do compose                  |
| `Cmd+K`      | Paleta global                              |
| `/`          | Foca search da fila                        |
| `[` `]`      | Snooze / fechar lead                       |
| `A`          | Atribuir (abre dropdown)                   |
| `T`          | Adicionar tag                              |
| `?`          | Mostra cheat sheet                         |
| `G + I`      | Vai pra inbox (de qualquer lugar)          |
| `G + D`      | Vai pra dashboard                          |
| `G + B`      | Vai pra builder                            |

### Cheat sheet UI
- Modal com tabela completa
- Acessível via `?` ou link no rodapé

### Edge cases
- Atalhos não disparam quando foco em input/textarea (exceto Cmd combinations)
- iOS Safari: Cmd vira Ctrl no Chromebook

---

## 3.7 Conversa: bubbles + áudio inline

### Bubbles
- Bot (esquerda): bg roxo escuro, texto branco
- User/lead (direita): bg cinza claro, texto preto
- Border-radius assimétrico (estilo WhatsApp)
- Avatar bot na primeira msg do bloco; lead idem
- Timestamp em hover (tooltip) + a cada 5min de gap

### Áudio inline player
- Waveform visualização (Wavesurfer.js ou customizado canvas)
- Play/pause central + tempo decorrido / total
- Click waveform → seek
- Speed: 1x / 1.5x / 2x toggle
- Auto-play próxima msg de áudio? config (default off)

### Estados
- Sending: opacity 60% + spinner
- Sent: ✓ cinza
- Delivered: ✓✓ cinza
- Read: ✓✓ azul
- Failed: ⚠️ vermelho + retry button

### Edge cases
- Áudio > 5min: limite WhatsApp 16MB (~10min)
- Áudio com formato não suportado: fallback "baixar áudio" link
- Browser sem WebAudio: fallback `<audio>` HTML5

---

## 3.8 Imagens expandíveis + carousel

### UX
- Thumbnail no bubble (max 200×200)
- Click → modal lightbox fullscreen
- Lightbox: zoom in/out, pan, download, próx/ant se múltiplas
- Múltiplas imagens em sequência: carousel mini horizontal no bubble

### Edge cases
- Imagem corrompida: placeholder "imagem indisponível"
- GIF animado: anima no thumbnail
- HEIC (iOS): converter pra JPEG no upload

---

## 3.9 Video player

### UX
- Thumbnail com play overlay
- Click → modal player (Plyr ou customizado)
- Controles: play/pause, scrub, volume, fullscreen, speed
- Suporta MP4, WebM

### Edge cases
- Video > 64MB: limite WhatsApp
- Sem audio: badge "🔇 sem som"

---

## 3.10 Documentos (PDF preview)

### UX
- Card com ícone + nome + tamanho + páginas
- Click → preview embed (PDF.js)
- Botão "Download"

### Suportados
- PDF (preview), DOCX (download), XLSX (download), TXT (preview inline)

---

## 3.11 Compose box com toolbar

### Layout
```
┌────────────────────────────────────────────────────────┐
│ [🤖 sugestão] [⚡ template] [📎 anexo] [😊] [🎤]      │
│ ┌─────────────────────────────────────────────────┐  │
│ │ Digite sua mensagem...                           │  │
│ │                                                  │  │
│ └─────────────────────────────────────────────────┘  │
│ Atalhos: Cmd+Enter envia · Esc cancela          [▶] │
└────────────────────────────────────────────────────────┘
```

### Funcionalidades
- Auto-resize do textarea
- Markdown shortcuts: `**bold**`, `_italic_`, `~strike~`
- Mention `@atendente` (notifica atendente)
- Insert variable `{{nome}}` autocomplete
- Char counter + warning aos 800/1000
- Drag-drop arquivo na área cola anexo

### Estados
- Sending: botão vira spinner, textarea readonly
- Failed: erro toast + retry

### Edge cases
- Mensagem > 4096 chars: split automático em múltiplas
- Emoji em texto: input nativo (🎉, 😊, ❤️)
- Paste imagem da clipboard: cola como anexo

---

## 3.12 Templates rápidos

### UX
- Botão `⚡` abre dropdown com lista
- Atalho `1`..`9` insere template 1-9
- Search no dropdown
- Click → cola no compose (não envia automaticamente)
- Template com `{{nome}}` substitui pelo lead atual

### Data Model (já existe `templates_msg`)
- Adicionar `shortcut_number` INT (1-9), `is_quick_reply` BOOLEAN

### Gerenciar
- `/settings/templates` — CRUD templates
- Categorias: saudação, oferta, fechamento, recuperação

---

## 3.13 Sugestão IA "responder por mim"

### UX
- Botão `🤖` no toolbar → mostra 3 sugestões inline
- Click sugestão → cola no compose (editável)
- Refresh → gera 3 novas
- Insights: "tom positivo / formal / urgente"

### Backend
- Gemini com contexto: últimas 10 msgs + persona do agente + intent detectado
- Cache 5min por lead pra economizar tokens
- Quota Gemini consumida

### Edge cases
- Lead novo (sem histórico): sugestões genéricas baseadas em fluxo
- Quota exceeded: botão desabilitado + tooltip "limite Gemini atingido"

### Métricas
- `compose.ai_suggestion_used` {accepted}
- `compose.ai_suggestion_refreshed`

---

## 3.14 Gravação de áudio inline

### UX
- Botão `🎤` (WebRTC API getUserMedia)
- Press hold to record (igual WhatsApp) ou tap to start/stop (config)
- Visual: waveform animado durante gravação
- Cancel: arrasta pra cima ou Esc
- Send: solta o botão / clica enviar
- Preview pré-envio: play + delete + send

### Edge cases
- Sem permissão mic: tooltip "permita microfone nas configurações"
- iOS Safari: requires user gesture (tap, não hold)
- Background tab: pausa gravação

### Backend
- Upload via multipart/form-data → S3/Cloudinary
- WebM/Opus (Chrome) ou MP4/AAC (Safari)
- Transcoding pra format aceito WhatsApp se necessário

---

## 3.15 Anexar mídia

### Tipos
- Imagem (JPG, PNG, WebP, HEIC)
- Vídeo (MP4, WebM)
- Documento (PDF, DOCX, XLSX, TXT)
- Áudio (MP3, OGG, WebM)

### Limites por tipo (WhatsApp)
- Imagem: 5MB
- Vídeo: 64MB
- Documento: 100MB
- Áudio: 16MB

### UX
- Click `📎` → file picker (multi-select max 10)
- Drag-drop área compose
- Preview thumbnails em grid
- Remove individual `[x]` em cada
- Send → todos enviados em sequência

### Edge cases
- Arquivo > limite: erro toast + skip
- Tipo não aceito: erro
- Upload falha 1 de 5: retry só do que falhou

---

## 3.16 Reactions (emoji em mensagens)

### UX
- Hover msg → menu mini com 😀 ❤️ 👍 🔥 ➕
- Click ➕ → picker emoji completo
- Reaction aparece embaixo do bubble com contador

### Data Model
```sql
CREATE TABLE message_reactions (
  message_id BIGINT REFERENCES mensagens(id),
  user_id INT,
  emoji VARCHAR(10),
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (message_id, user_id, emoji)
);
```

### Edge case
- Reactions enviam pra WhatsApp se provider suporta (Meta API: yes desde 2023)

---

## 3.17 Pin message no histórico

### UX
- Hover msg → menu `⋯ Pin`
- Banner topo da conversa: "📌 Pinned: <preview>"
- Click banner → scroll até msg
- Unpin: hover banner

### Data Model
```sql
ALTER TABLE mensagens ADD COLUMN pinned_at TIMESTAMP;
ALTER TABLE mensagens ADD COLUMN pinned_by INT;
```

### Limit
- Max 3 pinned por conversa

---

## 3.18 Painel contexto: dados do lead

### Card "Lead"
```
┌──────────────────────┐
│ avatar foto/inicial  │
│ Maria Silva          │
│ ♉ Touro · 38 anos    │
│ 📍 São Paulo, BR     │
│ 📞 +55 11 9...       │
│ 📧 maria@x.com       │
│ ⏱ Cliente desde 12/01│
└──────────────────────┘
[Editar]
```

### Campos editáveis (admin)
- Nome, signo, idade, cidade, telefone, email, tags, observações

### Custom fields (Pro+)
- Tenant pode definir campos extras (data nascimento, profissão, valor médio gasto, etc)

### Data Model
```sql
ALTER TABLE leads ADD COLUMN signo VARCHAR(20);
ALTER TABLE leads ADD COLUMN idade INT;
ALTER TABLE leads ADD COLUMN cidade VARCHAR(100);
ALTER TABLE leads ADD COLUMN custom_fields JSONB DEFAULT '{}';

CREATE TABLE tenant_lead_custom_fields (
  tenant_id VARCHAR(64),
  field_key VARCHAR(40),
  field_label VARCHAR(100),
  field_type VARCHAR(20),  -- text|number|date|select
  field_options JSONB,
  required BOOLEAN,
  PRIMARY KEY (tenant_id, field_key)
);
```

---

## 3.19 Painel contexto: jornada no fluxo

### Card "Jornada"
```
┌──────────────────────┐
│ Funil: Mistério Expr │
│ Nó atual: oferta_3   │
│ Há 12 minutos        │
│ ▁▂▄▆█ 5/9 nós        │
│ Próx: aguardando     │
│ resposta da oferta   │
└──────────────────────┘
[Forçar avanço] [Reset]
```

### Funcionalidades
- Mostra qual nó o lead está
- Tempo desde entrou no nó
- Progresso global no funil
- Próxima ação esperada
- Botões admin: forçar avanço, reset, pular pra nó X

### Backend
- Lê de `flow_runs` + `flow_run_events`

---

## 3.20 Painel contexto: gráfico de sentimento

### UX
```
┌──────────────────────┐
│ Sentimento últimas 10│
│ msgs                 │
│                      │
│ ●●●●●●●○○○ +6 / -2  │
│                      │
│ Tendência: ↗ pos     │
└──────────────────────┘
```

### Backend
- Já existe `mensagens.sentimento` (positivo/neutro/negativo)
- Card calcula últimas 10 + tendência

---

## 3.21 Painel contexto: IA sugere próxima ação

### UX
```
┌──────────────────────┐
│ 🪄 IA sugere         │
│                      │
│ "Maria está engajada │
│ no tema amor. Sugiro │
│ tiragem com cartas   │
│ Os Amantes + Sol +   │
│ Estrela. Mensagem:   │
│                      │
│ 'Maria, sinto que..."│
│                      │
│ [Usar sugestão]      │
└──────────────────────┘
```

### Backend
- Gemini com contexto: histórico + persona + jornada
- Refresh button manual
- Cache 10min por lead

---

## 3.22 Painel contexto: histórico de compra

### UX
```
┌──────────────────────┐
│ Compras (3)          │
│                      │
│ R$67 · Tarô Express  │
│ 12/03 · Cakto        │
│                      │
│ R$197 · Mistério VIP │
│ 28/02 · Stripe       │
│                      │
│ Total LTV: R$364     │
└──────────────────────┘
```

### Backend
- Query Cakto + Stripe webhooks já recebidos
- Tabela `payment_event_receipts` (já existe)

---

## 3.23 Painel contexto: notas livres

### UX
- Textarea inline editável (autosave debounce 1s)
- Markdown lite
- Histórico de versões (diff)
- Cada nota com timestamp

### Data Model
```sql
CREATE TABLE lead_notes (
  id BIGSERIAL PRIMARY KEY,
  lead_id BIGINT REFERENCES leads(id),
  author_user_id INT,
  content TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP
);
```

---

## 3.24 Lead scoring engine

### Algoritmo (peso)
- **Engagement (40%)**:
  - num_msgs últimos 7d (sigmoid 0-50)
  - tempo_resposta_user médio (rápido = +)
  - última msg < 1h: +20
- **Sentiment (20%)**:
  - sentiment positivo médio últimos 5
  - menções de objetivo ("preciso", "quero")
- **Funnel progress (20%)**:
  - profundidade no fluxo (% nós atravessados)
  - clicked oferta? +10
- **Comercial (20%)**:
  - LTV histórico
  - tem pagamento prévio: +15
  - tempo desde última compra

### Score = soma ponderada × 100

### Banda
- 70-100: 🔥 hot
- 40-69: 🟡 warm
- 0-39: ❄️ cold

### Implementação
```python
def compute_lead_score(lead) -> int:
    e = engagement_score(lead)  # 0-100
    s = sentiment_score(lead)
    f = funnel_score(lead)
    c = commercial_score(lead)
    raw = 0.4*e + 0.2*s + 0.2*f + 0.2*c
    return min(100, max(0, int(raw)))

def update_score_async(lead_id):
    # Job assíncrono toda vez que lead recebe ação
```

### Data Model
```sql
ALTER TABLE leads ADD COLUMN score_value INT DEFAULT 0;
ALTER TABLE leads ADD COLUMN score_band VARCHAR(10);
ALTER TABLE leads ADD COLUMN score_components JSONB;
ALTER TABLE leads ADD COLUMN score_updated_at TIMESTAMP;
CREATE INDEX ix_leads_score ON leads(tenant_id, score_value DESC);
```

### Edge cases
- Lead sem msgs: score 0
- Score < 0 (raro): clamp 0
- Recálculo em batch: nightly job recalcula todos

### Métricas
- `lead.score_recomputed`
- `lead.score_band_changed` {from, to}

---

## 3.25 Lead scoring banda visual

### UX
- Badge no card: 🔥 Hot / 🟡 Warm / ❄️ Cold
- Filtro de fila por banda
- Sort por score
- Hover: tooltip com breakdown components

---

## 3.26 Funnel waterfall por fluxo

### UX (`/flows/<id>/funnel`)
```
Funil: Mistério Express                Período: [30d ▾]
═══════════════════════════════════════════════════
                                                          
[1] Entrada                  ████████████ 1.247 leads
                                  ↓                       
[2] Saudação                 ████████░░░░ 1.089 (87%) ⬇ 13%
                                  ↓                       
[3] Coleta dados             █████░░░░░░░  642 (59%) ⬇ 41% 🔴
                                  ↓                       
[4] Oferta R$67              ████░░░░░░░░  412 (64%) ⬇ 36%
                                  ↓                       
[5] Pagamento confirmado     █░░░░░░░░░░░   89 (22%) ⬇ 78% 🔴
                                                          
Conversão geral: 7.1%        ⬇ 93%                       
═══════════════════════════════════════════════════
🔴 = drop alto (>30%) — clique pra ver sugestões
```

### Comportamentos
- Click em qualquer barra → drilldown: lista de leads que dropearam ali
- Hover: tooltip com tempo médio no nó, taxa de drop por hora do dia
- Filter: período, segmento de leads (banda score, canal)
- Compare modo: período atual vs anterior (linha pontilhada)

### Data Model
```sql
CREATE TABLE flow_node_visits (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT REFERENCES flow_runs(id),
  node_id VARCHAR(100),
  entered_at TIMESTAMP,
  exited_at TIMESTAMP,
  exit_reason VARCHAR(40)  -- response|timeout|exit|next
);
CREATE INDEX ix_visits_run ON flow_node_visits(run_id, entered_at);
CREATE INDEX ix_visits_flow_node ON flow_node_visits(node_id, entered_at);
```

### API
```
GET /api/flows/<id>/funnel?period=30d&segment=hot
  → {
    nodes: [{node_id, label, entered, exited, drop_pct}],
    overall_conversion_pct,
    period: {from, to}
  }
```

### Edge case
- Fluxo recém-criado < 50 runs: mostra "dados insuficientes (3/50)"

### Métricas
- `funnel.viewed` {flow_id, period}
- `funnel.node_drilldown` {node_id}

---

## 3.27 Drop heatmap nos nós do funil

### Sub-feature de 3.26
- Cor da barra varia: verde <20% drop, amarelo 20-40%, vermelho >40%
- Ícone 💡 em nós com drop alto → click abre painel "sugestões IA pra reduzir drop"

### Sugestões IA
- Prompt Gemini: "Aqui é o nó X com 41% drop. Conteúdo atual: [msg]. Sugira 3 reescritas pra aumentar engagement."
- Mostra inline + botão "criar A/B test"

---

## 3.28 A/B test em nó (criação)

### UX (no Builder)
- Click nó de mensagem → inspector → tab "A/B test"
- Botão "+ Adicionar variante B"
- Editor lado-a-lado: A original / B novo
- Slider split: 50/50 (default), 30/70, custom
- Define winning event: "responder", "click oferta", "pagar", custom
- Save → variant ativa
- Visual no canvas: nó com badge "A/B" amarelo

### Data Model
```sql
CREATE TABLE flow_node_experiments (
  id BIGSERIAL PRIMARY KEY,
  flow_id BIGINT,
  node_id VARCHAR(100),
  variant_a_text TEXT,
  variant_b_text TEXT,
  split_pct INT DEFAULT 50,
  winning_event VARCHAR(40),
  min_sample_size INT DEFAULT 50,
  confidence_threshold FLOAT DEFAULT 0.95,
  started_at TIMESTAMP DEFAULT NOW(),
  winner_picked_at TIMESTAMP,
  winner VARCHAR(1),  -- 'A' or 'B' or null
  status VARCHAR(20) DEFAULT 'running'  -- running|completed|stopped
);

CREATE TABLE flow_node_experiment_assignments (
  experiment_id BIGINT,
  lead_id BIGINT,
  variant VARCHAR(1),
  assigned_at TIMESTAMP DEFAULT NOW(),
  converted BOOLEAN DEFAULT FALSE,
  converted_at TIMESTAMP,
  PRIMARY KEY (experiment_id, lead_id)
);
```

### Lógica de assignment
```python
def get_variant(experiment_id, lead_id):
    # Determinístico: hash(experiment_id + lead_id) % 100 < split_pct ? A : B
    seed = f"{experiment_id}:{lead_id}"
    return 'A' if hash(seed) % 100 < experiment.split_pct else 'B'
```

### Limit
- Max 3 experimentos rodando simultaneamente por fluxo (estatística)

---

## 3.29 A/B test winner picking auto

### Lógica
- Job hourly verifica experimentos `status=running`:
  - Tem N=50 conversões cada variante? Sim:
    - Calcula chi-squared test
    - Se p-value < 0.05 e diff > 5%: declara winner
    - Se p-value > 0.05 mas N > 500: declara "no significant difference"
- Notifica admin: toast + email "Variante B venceu (12% vs 8%) — promover?"
- Botão "Promover B" → A vira B no fluxo, experimento arquivado
- Botão "Continuar" → segue rodando

### Estados
- running → completed_winner_a / completed_winner_b / completed_no_diff / stopped_manual

### Métricas
- `ab_test.created`
- `ab_test.winner_declared` {winner, lift_pct}
- `ab_test.promoted`

---

## 3.30 Heatmap de horário

### UX (`/analytics/heatmap`)
```
        00 01 02 03 ... 22 23
Dom  ░░ ░░ ▒▒ ░░     ▓▓ ▓▓
Seg  ░░ ░░ ░░ ░░     ██ ▓▓
Ter  ░░ ░░ ░░ ░░     ▓▓ ▒▒
Qua  ░░ ░░ ░░ ░░     ██ ▓▓
Qui  ░░ ░░ ░░ ░░     ██ ██
Sex  ▒▒ ░░ ░░ ░░     ▓▓ ██
Sáb  ▓▓ ▒▒ ░░ ░░     ██ ██
```

### Cores
- ░░ branco: 0 conversões
- ▒▒ verde claro: 1-5
- ▓▓ verde médio: 6-15
- ██ verde escuro: 16+

### Drilldown
- Click célula → lista de leads que converteram nesse slot
- Métricas: % de conversão por slot, msg sugerida automaticamente "agendar broadcast pra 22h domingo"

### Backend
- Agrega `eventos_audit` tipo `payment.confirmed` por dia_semana × hora
- Query 30d default

---

## 3.31 Best/worst message analysis

### UX (`/analytics/messages`)
- Tabela de mensagens enviadas únicas (hash do texto):
| Mensagem (preview)         | Vezes | % continuação | % drop | Sentiment resp |
|---------------------------|-------|---------------|--------|----------------|
| "Olá! Estou aqui pra t..." | 1.247 | 87%           | 13%    | +0.6           |
| "E aí, vamos começar?"     |   642 | 59%           | 41%    | +0.2           | 🔴
| ...                        |       |               |        |                |

- Sort por % drop desc (piores primeiro)
- Click → ver msg completa + 5 exemplos de leads que dropearam

### CTA
- "🪄 Reescrever com IA" → Gemini gera 3 variantes → botão "Criar A/B test"

### Backend
- Agrega `mensagens` por `MD5(texto)` (após normalização — lowercase, trim)
- Calcula taxa de continuação (lead respondeu nas próximas 24h)

---

## 3.32 Recovery suggestions visual

### Por quê
`recovery_engine.py` já existe mas é black-box.

### UX (card no Dashboard)
```
┌────────────────────────────────────────┐
│ 🔄 Recuperação                         │
│                                        │
│ 23 leads sumiram nos últimos 7 dias    │
│                                        │
│ • Maria — perdeu no nó oferta_3 há 3d │
│ • João — sem resposta há 5d           │
│ • Ana — clicou pix mas não pagou 2d   │
│                                        │
│ [🪄 Mandar mensagem auto] [Ver todos] │
└────────────────────────────────────────┘
```

### Fluxo "mandar mensagem auto"
1. IA gera msg personalizada por lead (contexto)
2. Modal review: lista com checkbox + msg preview editável
3. Aprovar em batch ou um-a-um
4. Send → todos via fluxo

### Backend
- Lê `recovery_engine` que já identifica leads em recovery
- Adiciona endpoint `POST /api/recovery/messages/generate {lead_ids}` → retorna msgs sugeridas

---

## 3.33 LTV por canal/UTM

### UX (`/analytics/channels`)
| Canal       | Leads | Pagos | Conv % | Receita | LTV avg |
|-------------|-------|-------|--------|---------|---------|
| TikTok ads  | 412   | 89    | 21%    | R$5.847 | R$65    |
| Instagram   | 287   | 34    | 12%    | R$2.244 | R$66    |
| Orgânico    | 198   | 42    | 21%    | R$3.234 | R$77    |
| Whatsapp ind| 89    | 28    | 31%    | R$2.156 | R$77    |

### Insights automáticos
- "TikTok dá mais leads mas menos LTV — qualidade?"
- "Indicação WhatsApp tem maior LTV — incentivar afiliação"

---

## 3.34 UTM tracking pipeline

### Captura
- Link da bio: `acassia.bio/maria?utm_source=tiktok&utm_campaign=promo_amor`
- Short link redireciona pra WhatsApp wa.me com first message contendo encoded UTM
- Bot lê primeira msg, extrai UTM, persiste em `lead.utm_*`

### Data Model
```sql
ALTER TABLE leads ADD COLUMN utm_source VARCHAR(60);
ALTER TABLE leads ADD COLUMN utm_medium VARCHAR(60);
ALTER TABLE leads ADD COLUMN utm_campaign VARCHAR(60);
ALTER TABLE leads ADD COLUMN utm_term VARCHAR(60);
ALTER TABLE leads ADD COLUMN utm_content VARCHAR(60);
ALTER TABLE leads ADD COLUMN referrer_url VARCHAR(500);
```

### Edge case
- Lead vem direto sem UTM: `utm_source = "direct"`

---

## 3.35 Lead source attribution

### UX
- Badge no card "🎵 TikTok" / "📷 IG" / "🔗 Direct"
- Filtro por canal na fila

### Multi-touch attribution (Pro+)
- Lead toca múltiplos canais antes de converter
- Atribui % a cada canal (first-touch, last-touch, linear, time-decay)
- Config no `/analytics/attribution`

---

## 3.36 Lead tags + segmentação

### UX
- Card lead: chips de tags + botão `+`
- Inspector: lista tags + autocomplete + criar nova
- Filtro de fila por tags
- Bulk action "adicionar tag a 23 selecionados"

### Smart tags (auto)
- IA sugere: "amor", "dinheiro", "saúde" baseado em conteúdo
- Tag automática: "vip" se LTV > R$500

### Data Model
```sql
CREATE TABLE lead_tags (
  lead_id BIGINT REFERENCES leads(id),
  tag VARCHAR(40),
  added_by INT,  -- null se sistema
  added_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (lead_id, tag)
);
CREATE INDEX ix_tags_tag ON lead_tags(tag);
```

### Segmentos
- Coleção salva de filtros + tags
- "Leads VIP que não compraram em 30d"
- Usado em broadcast targeting

---

## 3.37 Bulk actions em leads

### UX
- Checkbox no card → seleciona
- Top da fila: "23 selecionados → [Tag] [Atribuir] [Snooze] [Fechar] [Deletar] [Broadcast]"
- Atalho `Cmd+A` seleciona página visível
- "Selecionar todos os 247 que correspondem ao filtro"

### Ações
- Adicionar tag
- Atribuir atendente
- Snooze até data
- Fechar conversa
- Deletar (LGPD)
- Mandar broadcast (msg em massa)
- Mover pra fluxo

### Edge cases
- > 100: confirmação extra
- Bulk em > 1000: queue + email "concluído" pós-fato

---

## 3.38 Atribuição de lead a atendente

### UX
- Card lead: avatar do atendente atribuído (ou "?" se não atribuído)
- Click → dropdown de members
- "Atribuir a mim" atalho `A`
- Atribuição automática via routing rules (3.43)

### Data Model
```sql
ALTER TABLE leads ADD COLUMN assigned_to_user_id INT REFERENCES users(id);
ALTER TABLE leads ADD COLUMN assigned_at TIMESTAMP;
```

### Notificações
- Atendente notificado: badge no inbox + push opcional

---

## 3.39 SLA tracker

### Por quê
"Lead esperando há 2h sem resposta — perdeu cliente."

### Configuração (workspace)
- SLA por banda score: hot = 5min, warm = 1h, cold = 24h
- SLA por horário comercial (config 9-18 segunda-sexta)

### UX
- Badge no card: ⏰ "SLA em 12min" amarelo / "ATRASADO 23min" vermelho
- Dashboard: card "X leads em atraso"
- Email/push se atrasou

### Data Model
```sql
ALTER TABLE leads ADD COLUMN sla_due_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN sla_breached BOOLEAN DEFAULT FALSE;
```

---

## 3.40 Auto-snooze de leads

### Por quê
Lead respondeu "obrigado" à noite — não atender agora, snooze pra amanhã 9h.

### UX
- Botão `[` snooze → menu: "1h, 4h, amanhã 9h, segunda 9h, custom"
- Lead some da fila aberta, vai pra "Snoozed"
- Auto-volta no horário escolhido

### Smart snooze (IA)
- IA sugere "snooze pra amanhã 9h?" baseado em msg do lead

---

## 3.41 Macros (sequência de ações)

### Por quê
Atendente faz mesma sequência 100x/dia: "tag VIP → atribuir admin → mandar template oferta". Macro = 1 atalho.

### UX
- `/settings/macros` — CRUD macros
- Editor: sequência de actions (tag, atribuir, send template, snooze)
- Atalho personalizado: `Shift+1`..`9`
- Botão na conversa: "▶️ Aplicar macro"

### Data Model
```sql
CREATE TABLE inbox_macros (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  name VARCHAR(100),
  description TEXT,
  actions JSONB,  -- [{type, payload}]
  shortcut VARCHAR(20),
  created_by INT,
  is_team_macro BOOLEAN DEFAULT FALSE
);
```

---

## 3.42 Inbox notifications

### Tipos
- Nova mensagem inbound
- Lead atribuído a você
- @mention em nota interna
- SLA breached

### Canais
- In-app sino 🔔 com contador
- Sound (opt-in, config)
- Browser push (Service Worker)
- Email (digest 2x/dia, opt-in)
- Mobile push (PWA — Frente 5)

### UX
- Sino top header → dropdown últimas 20 notifications
- Click notification → vai pro lead

### Data Model
```sql
CREATE TABLE notifications (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  type VARCHAR(40),
  title VARCHAR(200),
  body TEXT,
  link VARCHAR(500),
  read_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_notif_user_unread ON notifications(user_id) WHERE read_at IS NULL;
```

### Preferências
```sql
CREATE TABLE notification_prefs (
  user_id INT PRIMARY KEY,
  inbox_inapp BOOLEAN DEFAULT TRUE,
  inbox_sound BOOLEAN DEFAULT TRUE,
  inbox_push BOOLEAN DEFAULT TRUE,
  inbox_email BOOLEAN DEFAULT FALSE,
  email_digest_freq VARCHAR(20) DEFAULT 'twice_daily'
);
```

---

## 3.43 Conversation routing rules

### Por quê
"Leads do TikTok vão pra Maria. Leads de horário noturno vão pro Pedro."

### UX (`/settings/routing`)
- Lista de regras com prioridade
- Rule editor:
  - IF: condições (canal, score, hora, tags, etc)
  - THEN: atribuir a (atendente, round-robin, lista)
- Testador: "esse lead seria roteado pra X"

### Data Model
```sql
CREATE TABLE routing_rules (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  name VARCHAR(100),
  conditions JSONB,
  action_type VARCHAR(40),  -- assign_user|assign_round_robin
  action_payload JSONB,
  priority INT,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 3.44 Conversation handoff (bot → humano)

### Por quê
Lead pergunta algo que bot não entende — escala pra humano.

### Triggers
- Lead digita keyword ("falar com humano", "atendente")
- Bot detecta intent "handoff" via Gemini
- Lead fica em silêncio em ponto crítico do funil
- Sentiment muito negativo

### UX
- Lead some da automação (fluxo pausado)
- Notificação pra atendente disponível
- Banner na conversa: "🤖 Bot pausado — assumindo conversa"
- Botão "voltar pro bot" reativa

### Data Model
```sql
ALTER TABLE leads ADD COLUMN bot_paused BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN bot_paused_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN bot_paused_reason VARCHAR(40);
```

---

## 3.45 CSAT post-conversa

### Por quê
"Como foi seu atendimento? ⭐⭐⭐⭐⭐"

### UX
- Após conversa fechada (manualmente ou auto após 24h sem msg), bot manda WA: "Avalie de 1-5"
- Lead responde: salva + opcional comentário
- Dashboard CSAT score médio

### Data Model
```sql
CREATE TABLE conversation_satisfaction (
  id BIGSERIAL PRIMARY KEY,
  lead_id BIGINT,
  score INT,  -- 1-5
  comment TEXT,
  attended_by_user_id INT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Metric
- CSAT médio /atendente, /fluxo, /workspace

---

## Resumo executivo Frente 3

### Tabelas novas (10)
1. `inbox_saved_views`
2. `tenant_lead_custom_fields`
3. `lead_notes`
4. `flow_node_visits`
5. `flow_node_experiments` + `flow_node_experiment_assignments`
6. `lead_tags`
7. `routing_rules`
8. `inbox_macros`
9. `notifications` + `notification_prefs`
10. `conversation_satisfaction`
11. `message_reactions`

### Alterações em existentes
- `leads`: `signo`, `idade`, `cidade`, `custom_fields`, `score_value`, `score_band`, `score_components`, `score_updated_at`, `utm_*`, `referrer_url`, `assigned_to_user_id`, `assigned_at`, `sla_due_at`, `sla_breached`, `bot_paused*`
- `mensagens`: `pinned_at`, `pinned_by`

### Endpoints novos: ~25 sob `/api/leads`, `/api/conversations`, `/api/flows/<id>/funnel`, `/api/analytics/*`

### Frontend
- Inbox redesign 3-painel
- `/analytics/heatmap`, `/analytics/messages`, `/analytics/channels`
- `/flows/<id>/funnel` waterfall
- Cmd+K palette
- Atalhos teclado completos
- 3 hooks novos: `useInboxQueue`, `useLeadContext`, `useConversation`

### Sprints sugeridos
- **A (sem 1-2)**: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.11, 3.12, 3.15, 3.18, 3.19, 3.42 — inbox core
- **B (sem 3-4)**: 3.9, 3.10, 3.13, 3.14, 3.20, 3.21, 3.22, 3.24, 3.25, 3.26, 3.27, 3.30, 3.36, 3.37, 3.38, 3.44 — intelligence + multi-feature
- **C (sem 5-6)**: 3.16, 3.17, 3.23, 3.28, 3.29, 3.31, 3.32, 3.33, 3.34, 3.35, 3.39, 3.40, 3.45 — analytics + advanced
- **D (sem 7+)**: 3.41, 3.43 — power user features
