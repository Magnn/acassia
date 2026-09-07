# Spec Acássia 360° — Frente 6: AI Copilot (Cigana Coach)

> IA não só responde leads — analisa o trabalho da tarólaga e sugere melhorias.
>
> Status: 📝 spec aprovada, 🚧 implementação não iniciada.
> Última atualização: 2026-04-29

## Inventário

| #    | Feature                                          | Crítico? | Sprint |
|------|--------------------------------------------------|----------|--------|
| 6.1  | Auto-copy generator (oferta → 5 variações)      | 🔴 sim   | A      |
| 6.2  | Lead summarizer (bullet do que importa)         | 🔴 sim   | A      |
| 6.3  | Daily briefing automation                        | 🟡 alto  | B      |
| 6.4  | Anomaly alerts (queda conversão)                 | 🟡 alto  | B      |
| 6.5  | Coach review (analisa fluxo + sugere)            | 🔴 sim   | B      |
| 6.6  | Reescrever msg ruim com IA                       | 🟡 alto  | A      |
| 6.7  | Generate persona (entrada user → persona)       | 🟡 alto  | A      |
| 6.8  | Translate cultural (msg → linguagem espiritual)  | 🟢 médio | C      |
| 6.9  | Auto-tagging de leads                            | 🟡 alto  | B      |
| 6.10 | Smart routing (classifica lead → fluxo certo)   | 🟡 alto  | B      |
| 6.11 | Voice transcription (áudio do lead → texto)     | 🔴 sim   | A      |
| 6.12 | Image OCR + analysis (palma da mão?)             | 🟢 médio | D      |
| 6.13 | Sentiment alert (lead irritado → atende rápido) | 🟡 alto  | B      |
| 6.14 | Predictive lead scoring (ML)                     | 🟢 médio | D      |
| 6.15 | Predictive conversion (vai pagar?)               | 🟢 médio | D      |
| 6.16 | Auto-follow-up generation                        | 🟡 alto  | C      |
| 6.17 | Best time to send (per-lead)                     | 🟡 alto  | C      |
| 6.18 | Topic clustering (qual tema converte mais)      | 🟢 médio | C      |
| 6.19 | A/B test winner declaration                      | 🟡 alto  | B      |
| 6.20 | Coach proactive notifications                    | 🟡 alto  | B      |
| 6.21 | Conversation summary (long thread → 3 bullets)  | 🟡 alto  | B      |
| 6.22 | Reply quality scoring                            | 🟢 médio | C      |
| 6.23 | Goal tracker (meta semanal/mensal)               | 🟡 alto  | C      |
| 6.24 | Coach weekly report (email digest)               | 🟢 médio | C      |
| 6.25 | Spam/abuse detection (lead message classifier)  | 🟡 alto  | B      |

---

## 6.1 Auto-copy generator

### Por quê
Tarólogo trava em "como escrever oferta de R$197?" — IA gera 5 variações em 10s.

### UX (no Builder ou Studio)
- Em qualquer textarea de mensagem: botão `🪄 Gerar com IA`
- Modal:
  - Pergunta: "O que você quer comunicar?"
  - Inputs auxiliares (opcional):
    - Persona ativa: pré-preenchido
    - Tom: casual / formal / místico (slider)
    - Comprimento: curto / médio / longo
    - Inclui CTA?
- Click "Gerar 5 variações" → Gemini retorna 5 textos
- User escolhe um (click) ou edita inline
- Botão "Gerar mais 5" ou "Refazer com tom Y"

### Backend
- Prompt template:
  ```
  Você é especialista em copy persuasiva pra WhatsApp espiritual/tarot.
  Gere 5 variações da seguinte mensagem, em pt-BR, max 200 chars cada.
  Persona da tarólaga: {persona}
  Tom: {tom}
  Comprimento: {comprimento}
  
  Intenção: {user_input}
  
  Retorne JSON: {variations: [{text, style_label}]}
  ```
- Cache: 1h por (input + params)
- Quota Gemini consumida

### Edge cases
- Input vazio: erro "descreva o que você quer"
- 5 variações muito iguais: regenera com `temperature=0.9` mais alta
- Output não JSON: parse fallback + retry

### Métricas
- `ai.copy_generated` {chars, comprimento}
- `ai.copy_variation_used` {position 1-5}
- `ai.copy_regenerated`

---

## 6.2 Lead summarizer

### Por quê
Atendente abre lead com 50 mensagens — não vai ler tudo. "🪄 Resumir" dá bullet do que importa em 5s.

### UX
- Botão `🪄 Resumir conversa` no panel contexto
- Click → loading → cards:
  ```
  ┌──────────────────────────────────┐
  │ Resumo de Maria (47 mensagens)  │
  │                                  │
  │ ▸ Pergunta principal: amor — quer│
  │   saber se ex vai voltar         │
  │ ▸ Já contou: viúva 2 anos,       │
  │   conheceu Pedro mês passado     │
  │ ▸ Fase: ofereceu R$67, ela está  │
  │   indecisa (3 dias sem resposta) │
  │ ▸ Sentiment: ansiedade alta      │
  │ ▸ Próxima ação sugerida: msg de  │
  │   recuperação com tom acolhedor  │
  │                                  │
  │ [Refresh] [Compartilhar]         │
  └──────────────────────────────────┘
  ```

### Backend
- Prompt:
  ```
  Resuma esta conversa de WhatsApp em 5 bullets max:
  - Pergunta principal do lead
  - Informações pessoais relevantes
  - Estado atual da conversa (oferta, pagamento, etc)
  - Sentiment dominante
  - Sugestão de próxima ação
  
  Conversa: {messages}
  ```
- Cache 5min
- Refresh manual

### Métricas
- `ai.lead_summary_generated`
- `ai.lead_summary_refreshed`

---

## 6.3 Daily briefing automation

### Por quê
Tarólaga abre app de manhã — "o que aconteceu enquanto eu dormia?" — IA prepara briefing.

### UX (push notification + dashboard card)
- 8h da manhã (timezone user): push "📊 Bom dia! Seu briefing tá pronto"
- Card top do dashboard:
  ```
  ☀️ Briefing 28/04
  
  • 23 leads novos (▲ 12% vs ontem)
  • 5 vendas R$835 (▲ 30%)
  • 3 hot leads precisam atenção:
    → Maria (R$197 oferta pendente há 3h)
    → João (clicou pix sem pagar 1h)
    → Ana (pergunta amor sem resposta)
  • Sugestão do dia: "Aproveite a lua cheia
    em Câncer pra trabalhos amorosos —
    aumentei conversão 30% em testes"
  • Anomalia detectada: drop conversão 25%
    no nó oferta_3 — quer investigar?
  
  [Ver leads hot] [Investigar anomalia]
  ```

### Backend
- Cron 7am timezone user
- Agrega dados dia anterior + identifica eventos importantes
- Gemini compõe texto humanizado

### Configuração
- User pode customizar: horário, conteúdo, frequência (diário/semanal)

### Métricas
- `briefing.generated`
- `briefing.opened`
- `briefing.cta_clicked` {cta}

---

## 6.4 Anomaly alerts

### Por quê
Conversão caiu 30% nas últimas 24h — user precisa saber AGORA.

### Sinais monitorados
- **Drop conversão** > 25% (vs média 7d)
- **Drop msgs respondidas** > 30%
- **Pico erros** (provider WA falha)
- **Failed payments** anormais
- **Spam detection** > 5% mensagens

### UX
- Notification push + email + dashboard card vermelho
- Card "🚨 Anomalia detectada":
  ```
  Sua conversão caiu 30% nas últimas 24h.
  
  Possível causa: nó oferta_3 está com 60% drop
  (vs 35% na semana passada).
  
  Ação sugerida:
  → Reverteu mudança recente no nó X?
  → Quer reescrever msg com IA?
  
  [Investigar] [Dispensar]
  ```

### Backend
- Job hourly compara métricas atual vs baseline (7d média)
- Threshold por kind
- Persiste em `anomaly_alerts` table

### Data Model
```sql
CREATE TABLE anomaly_alerts (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  alert_type VARCHAR(40),
  severity VARCHAR(10),
  current_value FLOAT,
  baseline_value FLOAT,
  deviation_pct FLOAT,
  context JSONB,
  detected_at TIMESTAMP DEFAULT NOW(),
  acknowledged_at TIMESTAMP,
  resolved_at TIMESTAMP
);
```

### Edge cases
- False positive: user clica "isso é normal" → adiciona ao baseline
- Tenant sem histórico (recém-criado): pula até ter 7d
- Anomalia em fim-de-semana: ajusta baseline (sazonalidade)

---

## 6.5 Coach review

### Por quê
"Cigana Coach analisou seu funil e tem 3 sugestões."

### UX (`/coach/review`)
- Card "Pronto pra revisar seu funil?"
- Click "Gerar review" → 30s loading → relatório:
  ```
  ┌──────────────────────────────────────────┐
  │ Coach Review — Funil Mistério Express    │
  │                                          │
  │ Analisei 247 conversas dos últimos 30d. │
  │                                          │
  │ ✅ Pontos fortes:                       │
  │ • Saudação tem alta resposta (87%)       │
  │ • Persona alinhada com público           │
  │                                          │
  │ ⚠️ Oportunidades:                       │
  │ 1. Nó "oferta_3" tem drop 41% (alto):   │
  │    msg muito longa, sugestão IA →        │
  │    [ver sugestão]                        │
  │                                          │
  │ 2. Você não usa A/B test:                │
  │    poderia melhorar conversão 15-30%.    │
  │    [criar A/B agora]                     │
  │                                          │
  │ 3. Lua cheia próxima (12/05) — sem       │
  │    automação ativada. Concorrentes       │
  │    bombam nesse dia.                     │
  │    [criar trigger lunar]                 │
  │                                          │
  │ Score do funil: 72/100                   │
  │                                          │
  │ [Aplicar sugestões] [Re-analizar]        │
  └──────────────────────────────────────────┘
  ```

### Backend
- Prompt grande:
  ```
  Você é o Coach da Acássia. Analise o funil X.
  
  Métricas:
  - Total leads: 247
  - Conversão: 7%
  - Drops por nó: ...
  - Mensagens enviadas: ...
  - Sentiment médio: ...
  
  Fluxo:
  [JSON do blueprint]
  
  Identifique:
  - 2 pontos fortes
  - 3-5 oportunidades de melhoria
  - Score 0-100
  - Sugestões acionáveis
  
  Tom: amigável, motivacional, prático.
  ```
- Output JSON estruturado pra renderizar

### Cadence
- Gerável on-demand
- Auto-mensal (envia email digest)

### Métricas
- `coach.review_generated`
- `coach.suggestion_applied` {type}
- `coach.score` {value}

---

## 6.6 Reescrever msg ruim com IA

### Por quê
Em `/analytics/messages` (3.31), msg com drop alto → click "🪄 Reescrever".

### UX
- Modal:
  ```
  Mensagem original (41% drop):
  ┌─────────────────────────────────┐
  │ "E aí, vamos começar?"          │
  └─────────────────────────────────┘
  
  Sugestões:
  ┌─────────────────────────────────┐
  │ A) "Estou pronta pra te receber │
  │     na sua jornada — começamos?"│
  └─────────────────────────────────┘
  ┌─────────────────────────────────┐
  │ B) "Reservei um momento pra     │
  │     você. Vamos descobrir?"     │
  └─────────────────────────────────┘
  ┌─────────────────────────────────┐
  │ C) "Sinto sua energia próxima.  │
  │     Pronta pra começar?"        │
  └─────────────────────────────────┘
  
  [Aplicar A/B test] [Substituir direto]
  ```

### Backend
- Prompt: persona da tarólaga + msg atual + drop rate + 3 variações com tons distintos
- Botão "Aplicar A/B test" → cria experimento (3.28) com original vs winner

---

## 6.7 Generate persona

### Já coberto em Frente 5.4
- IA gera persona completa baseada em 5 perguntas
- Pode regenerar variações

---

## 6.8 Translate cultural

### Por quê
Tarólogo escreve "Te ajudo na sua dúvida" — IA reescreve místico: "Vou guiar tua alma na encruzilhada".

### UX
- Em qualquer textarea: botão `✨ Místico`
- Click → IA reescreve + opções de intensidade

### Backend
- Prompt:
  ```
  Reescreva esta mensagem com linguagem místico-espiritual brasileira,
  mantendo o significado mas adicionando profundidade poética.
  Intensidade: {leve|média|forte}
  
  Original: {text}
  ```

---

## 6.9 Auto-tagging de leads

### Por quê
Tarólogo não tem tempo de tagear manualmente. IA classifica.

### Backend
- Job assíncrono em cada lead novo / após N msgs:
  - Lê histórico
  - Gemini classifica em categorias predefinidas + sugere tags custom
  - Persiste em `lead_tags` (com `added_by=null` indicando IA)

### Categorias auto
- Tema: amor / dinheiro / saúde / família / espiritualidade
- Estágio: novo / engajado / qualificado / cliente / churnado
- Persona: ansioso / pragmático / cético / místico

### Limit
- Max 5 tags auto por lead

### Métricas
- `ai.lead_tagged_auto` {tag_count}

---

## 6.10 Smart routing (classifica lead → fluxo certo)

### Por quê
Lead chega via número genérico — qual fluxo aplicar?

### Lógica
- Bot pergunta inicialmente: "Qual sua dúvida hoje?"
- Lead responde
- Gemini classifica intent → escolhe fluxo certo (mapeamento config)

### Configuração (admin)
- `/settings/smart-routing`:
  - "Se intent = amor → fluxo Tarô Amor"
  - "Se intent = grana → fluxo Mistério Reservado"
  - "Default → fluxo Geral"

### Edge cases
- Múltiplos intents: escolhe o mais relevante (priority order)
- Confiança baixa: usa default

---

## 6.11 Voice transcription

### Por quê
Lead manda áudio. Tarólogo precisa entender rápido sem ouvir 3min.

### Provider
- OpenAI Whisper API ou Deepgram (~$0.006/min)
- Self-hosted Whisper (custo zero, mais lento)

### UX
- Auto-transcreve todo áudio inbound
- Mostra texto abaixo do player com indicador "📝 transcrito por IA"
- Click play ainda funciona normal

### Backend
- Worker async: detecta áudio inbound → chama Whisper → persiste em `mensagens.transcription`
- Idioma auto-detect (priorizar pt-BR)

### Data Model
```sql
ALTER TABLE mensagens ADD COLUMN transcription TEXT;
ALTER TABLE mensagens ADD COLUMN transcription_language VARCHAR(10);
ALTER TABLE mensagens ADD COLUMN transcription_confidence FLOAT;
ALTER TABLE mensagens ADD COLUMN transcribed_at TIMESTAMP;
```

### Edge cases
- Áudio com música: transcreve só voz
- Idioma desconhecido: mostra "transcrição não disponível"
- Confiança baixa: warning "transcrição imprecisa"
- Custo controlado: cap por tenant/mês (Pro+ só)

### Métricas
- `voice.transcribed` {duration_s, language}
- `voice.transcription_failed` {reason}

---

## 6.12 Image OCR + analysis

### Casos de uso
- Lead manda foto da palma da mão → IA analisa linhas (quiromancia)
- Lead manda foto de carta tirada por outro → reconhece carta
- Lead manda screenshot de outro app → extrai contexto

### Implementação (V2 — não MVP)
- Gemini Vision multimodal
- Prompt context-aware (palma vs carta vs screenshot)

### Edge cases
- Foto inadequada: "não consigo ver claramente — pode mandar com mais luz?"
- Conteúdo NSFW: bloqueia + alerta admin

---

## 6.13 Sentiment alert

### Por quê
Lead mandou msg furiosa — atendente humano precisa intervir AGORA, não amanhã.

### Detecção
- Sentiment classifier em cada msg inbound
- Trigger se: sentiment = muito_negativo + palavras-chave (cancelar, reembolso, lixo, fraude)

### Ação
- Marca lead como `urgent_attention=true`
- Notification push (alta prioridade) pra atendente
- Inbox: lead vai pro topo com badge 🚨
- (Opcional) bot pausa fluxo — handoff humano

### Data Model
```sql
ALTER TABLE leads ADD COLUMN urgent_attention BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN urgent_reason VARCHAR(100);
ALTER TABLE leads ADD COLUMN urgent_detected_at TIMESTAMP;
```

### Métricas
- `sentiment.urgent_alert` {tenant_id}
- `sentiment.urgent_resolved` {duration_s}

---

## 6.14 Predictive lead scoring (ML)

### Por quê
Score atual é heurístico (Frente 3.24). ML pode prever melhor com dados históricos.

### Implementação (V2)
- Feature engineering: 20-30 features de cada lead (msgs, tempo, signo, fase lunar, hora, persona, etc)
- Modelo: gradient boosting (XGBoost) ou logistic regression
- Train: dataset histórico de leads que pagaram vs não pagaram
- Predict: score 0-100 + confidence

### Plataforma
- Hospedar modelo: HuggingFace, Replicate, ou self-hosted
- Retreina mensal com novos dados

### Data Model
```sql
ALTER TABLE leads ADD COLUMN ml_score INT;
ALTER TABLE leads ADD COLUMN ml_score_updated_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN ml_features JSONB;  -- pra debug
```

### Edge cases
- Tenant com poucos dados: não usa ML, fallback heurístico
- Modelo "vê" dado novo (signo raro): retorna baixa confidence

---

## 6.15 Predictive conversion

### Sub-feature de 6.14
- Específico: "vai pagar nas próximas 24h?"
- Output: probability + reasoning ("alta engagement + sentiment positivo")

### UX
- Badge no card lead: "🔥 87% conversão prevista"
- Sort por probability: focar nos mais quentes

---

## 6.16 Auto-follow-up generation

### Por quê
Lead sumiu há 3 dias — IA gera msg de follow-up personalizada.

### UX
- Recovery dashboard: lista leads inactive
- "🪄 Mandar follow-up" gera msg (igual 3.32 mas integrado IA-first)
- Aprovar em batch

### Backend
- Gemini com contexto: histórico + razão provável de inatividade + persona
- Cada lead recebe msg única, não template

### Edge cases
- Lead já recebeu follow-up: não manda de novo (cap 1/semana)

---

## 6.17 Best time to send (per-lead)

### Por quê
Cada lead tem horário ideal de resposta. IA descobre.

### Lógica
- Analisa histórico: quando o lead respondeu mais rápido?
- Identifica padrão: "Maria responde 21h-23h em dias úteis"
- Aplica em broadcasts agendados pra esse lead

### UX
- Card contexto lead: "⏱ Melhor horário: 22h domingos"
- Broadcast scheduler: opção "horário ótimo de cada lead" (calcula individualmente)

---

## 6.18 Topic clustering

### Por quê
"Quais temas convertem mais no meu negócio?"

### Backend
- Job mensal: clustering das mensagens dos leads (k-means ou similar)
- Identifica clusters: "amor", "ex-namorado", "dinheiro", "filhos", etc
- Calcula conversão por cluster

### UX (`/analytics/topics`)
- Bubble chart: tamanho = volume, cor = conversão
- Insight: "tema 'ex' tem 30% conversão vs 12% média — investir aqui"

---

## 6.19 A/B test winner declaration

### Já coberto em Frente 3.29
- Incluso aqui pq é AI-driven (chi-squared automático)

---

## 6.20 Coach proactive notifications

### Tipos
- "Você tem 3 leads quentes esperando há > 1h"
- "Sua msg X teve queda de conversão — investigar?"
- "Lua cheia em 3 dias — aproveitar?"
- "Maria voltou após 30d sumida — atender?"

### UX
- Sino com badge "Coach"
- Drawer dedicado "💡 Sugestões do Coach"

---

## 6.21 Conversation summary

### Já coberto em 6.2 mas:
- Versão "long thread → 3 bullets" pra leads com 100+ mensagens

---

## 6.22 Reply quality scoring

### Por quê
Ajuda atendente humano a melhorar — feedback após enviar mensagem.

### UX
- Após atendente enviar msg: badge mini "Coach: msg 8/10 — ótimo!"
- Tooltip: "tom alinhado com persona, comprimento adequado"
- Score baixo: "msg um pouco genérica — quer reescrever?"

### Backend
- Gemini avalia msg vs persona + contexto
- Não bloqueia envio (só sugere)

---

## 6.23 Goal tracker

### Por quê
"Minha meta esse mês é R$5k" — visualizar progresso engaja.

### UX (`/goals`)
- User define meta: receita, leads, vendas
- Dashboard: barra progresso + projeção
- Notification "75% da meta — vai conseguir!"

### Data Model
```sql
CREATE TABLE user_goals (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  metric VARCHAR(40),  -- revenue|leads|sales|conversion
  target_value FLOAT,
  period VARCHAR(20),  -- weekly|monthly|yearly
  starts_on DATE,
  ends_on DATE,
  achieved_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 6.24 Coach weekly report

### Email digest semanal (segunda 9h):
- Resumo da semana
- Pontos altos / baixos
- Comparação semana anterior
- Top 3 sugestões pra próxima

---

## 6.25 Spam/abuse detection

### Por quê
Lead bot/spam consome quota e polui inbox.

### Sinais
- Mesma msg copiada de N leads
- Padrão URL spam
- Idioma estranho
- Velocidade inhumana (10 msgs/seg)

### Ação
- Marca lead `is_spam=true`
- Some da fila default
- Refund quota (não cobra)

### Data Model
```sql
ALTER TABLE leads ADD COLUMN is_spam BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN spam_score FLOAT;
ALTER TABLE leads ADD COLUMN spam_detected_at TIMESTAMP;
```

---

## Resumo executivo Frente 6

### Tabelas novas (3)
1. `anomaly_alerts`
2. `user_goals`

(maior parte é alteração de tabelas existentes)

### Alterações em existentes
- `mensagens`: `transcription`, `transcription_language`, `transcription_confidence`, `transcribed_at`
- `leads`: `urgent_attention`, `urgent_reason`, `urgent_detected_at`, `ml_score`, `ml_score_updated_at`, `ml_features`, `is_spam`, `spam_score`, `spam_detected_at`

### Provider integrations
- Whisper (transcription) — Pro+
- Gemini Vision (image OCR) — V2
- Self-hosted ML model (XGBoost) — V2

### Endpoints novos: ~20

### Frontend
- Coach drawer + tab
- AI generation buttons (🪄) em todos textareas relevantes
- `/coach/review` page
- `/analytics/topics`, `/goals` pages
- Sentiment urgent badge nos leads

### Sprints
- **A (sem 1-2)**: 6.1, 6.2, 6.6, 6.7, 6.11 — IA generative core
- **B (sem 3-4)**: 6.3, 6.4, 6.5, 6.9, 6.10, 6.13, 6.19, 6.20, 6.21, 6.25 — coach + sentiment + classification
- **C (sem 5-6)**: 6.8, 6.16, 6.17, 6.18, 6.22, 6.23, 6.24 — advanced
- **D (sem 7+)**: 6.12, 6.14, 6.15 — ML/Vision V2
