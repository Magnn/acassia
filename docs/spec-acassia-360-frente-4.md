# Spec Acássia 360° — Frente 4: Niche-Specific (Moat Espiritual)

> O que faz competidor genérico de WhatsApp NÃO conseguir te copiar.
>
> Status: 📝 spec aprovada, 🚧 implementação não iniciada.
> Última atualização: 2026-04-29

## Inventário

| #    | Feature                                          | Crítico? | Sprint |
|------|--------------------------------------------------|----------|--------|
| 4.1  | Lunar phase calendar (atual + forecast 365d)    | 🟡 alto  | A      |
| 4.2  | Lunar-trigger nodes (fluxo dispara por fase)    | 🟡 alto  | A      |
| 4.3  | Astrologia: signo do sol básico                 | 🔴 sim   | A      |
| 4.4  | Mapa astral: captura nascimento                 | 🟡 alto  | B      |
| 4.5  | Mapa astral: cálculo + rendering visual         | 🟡 alto  | B      |
| 4.6  | Mapa astral: interpretação GPT contextual       | 🟡 alto  | B      |
| 4.7  | Tarot virtual: deck digital (78 cartas)         | 🔴 sim   | A      |
| 4.8  | Tarot virtual: simulador 1/3/5/10 cartas        | 🔴 sim   | A      |
| 4.9  | Tarot virtual: leitura GPT contextual           | 🔴 sim   | A      |
| 4.10 | Tarot virtual: histórico de leituras por lead   | 🟡 alto  | B      |
| 4.11 | Numerologia: cálculo número da vida             | 🟢 médio | B      |
| 4.12 | Numerologia: análise GPT                        | 🟢 médio | B      |
| 4.13 | Horóscopo diário automático (broadcast)         | 🔴 sim   | B      |
| 4.14 | Voice cloning ElevenLabs                        | 🔴 sim   | A      |
| 4.15 | Voice cloning enrollment (gravar 1min)          | 🔴 sim   | A      |
| 4.16 | Audio messages na voz clonada                   | 🔴 sim   | A      |
| 4.17 | Audio library categorizada                      | 🟡 alto  | B      |
| 4.18 | Stable Diffusion: aura/imagem espiritual        | 🟢 médio | C      |
| 4.19 | Sentiment intent espiritual (amor/grana/saúde)  | 🟡 alto  | B      |
| 4.20 | Specialized prompts (cigana, tarô, espirita)    | 🔴 sim   | A      |
| 4.21 | Glossário espiritual no GPT                     | 🟡 alto  | B      |
| 4.22 | Calendário de ritos/datas espirituais           | 🟢 médio | C      |
| 4.23 | Onboarding kit "monte sua tarot card"           | 🟢 médio | C      |
| 4.24 | Comunidade/grupos espirituais                   | 🟢 médio | D      |
| 4.25 | Capture data nascimento via WhatsApp natural    | 🟡 alto  | B      |
| 4.26 | Smart greeting baseado em fase lunar/signo      | 🟡 alto  | B      |
| 4.27 | "Mensagem do dia" personalizada                 | 🟡 alto  | C      |
| 4.28 | Tiragem agendada (próxima lua cheia)            | 🟢 médio | C      |
| 4.29 | Card draw history + tendências                  | 🟢 médio | C      |
| 4.30 | Acessibilidade espiritual (voice-only mode)     | 🟢 médio | D      |

---

## 4.1 Lunar phase calendar

### Por quê
Tarólogos usam fases lunares pra agendar tiragens, rituais. Plataforma nativa = facilidade.

### Backend
- Biblioteca: `pyswisseph` (Swiss Ephemeris) ou `ephem` (PyEphem) ou API externa
- Cálculo determinístico: dado timestamp UTC + lat/lon, retorna fase lunar
- Pré-calcula 365 dias forward + 30 backward em cron diário

### Data Model
```sql
CREATE TABLE lunar_phases (
  date DATE PRIMARY KEY,
  phase_name VARCHAR(20),  -- nova|crescente|cheia|minguante
  illumination_pct FLOAT,
  zodiac_sign VARCHAR(20),  -- "Touro" etc (lua no signo X)
  is_special BOOLEAN,  -- super lua, eclipse, etc
  special_label VARCHAR(60)
);
```

### API
```
GET /api/lunar/today → {date, phase, illumination, zodiac, is_special}
GET /api/lunar/calendar?from=2026-04-01&to=2026-12-31 → [{date, phase, ...}]
GET /api/lunar/next-full-moon → {date, days_until}
```

### UX (`/calendar/lunar`)
- Calendário mensal visual com fases
- Ícone por fase 🌑🌒🌓🌔🌕🌖🌗🌘
- Click dia → painel lateral: "Lua cheia em Touro — propício pra trabalhos de prosperidade"
- Próximas datas especiais: super lua, eclipse, etc

### Edge cases
- Timezone: cálculo em UTC, exibição local (`users.timezone`)
- Hemisférios: fase é mesma globalmente, só visual espelha em S vs N

### Métricas
- `lunar.calendar_viewed`
- `lunar.special_event_alert_sent`

---

## 4.2 Lunar-trigger nodes (fluxo)

### Por quê
"Quero mandar broadcast só na lua cheia."

### UX (Builder)
- Tipo de nó novo: 🌕 "Gatilho lunar"
- Inspector:
  - Trigger: lua cheia / nova / crescente / minguante / eclipse / super lua
  - Janela: 24h antes / 48h antes / dia exato
  - Filtro de leads: tags, signo, segmento
- Conecta com nó de mensagem normalmente

### Backend
- Cron hourly verifica próximas 24h: tem trigger ativo?
- Sim → enfileira execução do fluxo pra cada lead matching no horário certo

### Data Model
```sql
CREATE TABLE lunar_triggers (
  id BIGSERIAL PRIMARY KEY,
  flow_id BIGINT,
  node_id VARCHAR(100),
  trigger_phase VARCHAR(20),
  window_hours INT,
  filter_segment_id BIGINT,
  active BOOLEAN DEFAULT TRUE,
  last_fired_at TIMESTAMP
);
```

---

## 4.3 Astrologia: signo do sol

### Captura
- Bot pergunta naturalmente: "Que dia você nasceu?"
- Parseia data → calcula signo
- Persiste em `leads.signo`, `leads.birth_date`

### Data Model
```sql
ALTER TABLE leads ADD COLUMN birth_date DATE;
ALTER TABLE leads ADD COLUMN birth_time TIME;
ALTER TABLE leads ADD COLUMN birth_place VARCHAR(200);
ALTER TABLE leads ADD COLUMN birth_lat FLOAT;
ALTER TABLE leads ADD COLUMN birth_lon FLOAT;
ALTER TABLE leads ADD COLUMN signo VARCHAR(20);  -- Touro, Áries, etc
ALTER TABLE leads ADD COLUMN ascendente VARCHAR(20);
ALTER TABLE leads ADD COLUMN lua VARCHAR(20);
```

### Helpers
```python
def compute_sun_sign(birth_date: date) -> str:
    # Tabela hardcoded: Áries 21/03-19/04 etc
def compute_ascendant(birth_date, birth_time, lat, lon) -> str:
    # Swiss Ephemeris

ZODIAC = {
    "Áries": {"element": "fogo", "ruler": "Marte", "polarity": "positive", ...},
    ...
}
```

### Uso
- Personalizer GPT recebe signo no contexto
- "Mensagem para Maria, signo Touro" → tom adaptado

---

## 4.4 Mapa astral: captura nascimento

### UX
- Bot pergunta gradual:
  1. "Qual seu nome?"
  2. "Que dia você nasceu? (DD/MM/AAAA)"
  3. "A que horas? (se souber, mais preciso)"
  4. "Onde nasceu? (cidade/país)"
- Cada resposta valida + persiste
- Se não sabe horário: usa 12:00 médio + alerta "ascendente impreciso"
- Geocoding: cidade → lat/lon (Nominatim/Mapbox)

### Edge cases
- Data inválida: bot pede de novo gentilmente
- Horário "manhã/tarde": parseia heurística
- Cidade ambígua: bot lista 3 opções

---

## 4.5 Mapa astral: cálculo + rendering

### Cálculo
- Input: birth_date, birth_time, lat, lon
- Output: posições de Sol, Lua, Mercúrio, Vênus, Marte, Júpiter, Saturno, Urano, Netuno, Plutão em signos + casas
- Aspectos: conjunções, oposições, trígonos, quadraturas, sextis
- Lib: `pyswisseph`

### Data Model
```sql
CREATE TABLE lead_natal_charts (
  lead_id BIGINT PRIMARY KEY REFERENCES leads(id),
  computed_at TIMESTAMP DEFAULT NOW(),
  positions JSONB,  -- {sun: {sign, deg, house}, moon: {...}, ...}
  aspects JSONB,    -- [{p1, p2, type, orb}]
  chart_svg TEXT    -- pre-rendered SVG cacheado
);
```

### Rendering
- SVG circular com 12 casas + planetas
- Lib: render server-side com `svgwrite` ou client-side React
- Color por elemento (fogo/terra/ar/água)
- Click planeta → tooltip com info

### UX
- Tab "Mapa astral" no contexto do lead
- Botão "Enviar pro lead" → manda imagem PNG via WhatsApp
- Compartilhar link público (read-only)

### Edge case
- Birth time desconhecido: marca casas como pontilhadas + aviso

---

## 4.6 Mapa astral: interpretação GPT

### Backend
- Prompt template:
  ```
  Você é uma astróloga experiente. Interprete o mapa abaixo de forma 
  empática e prática (não muito técnica), em pt-BR, max 200 palavras.
  
  Sol em [signo] casa [N], Lua em ..., Ascendente ..., aspectos: ...
  
  Foque em: personalidade, vida amorosa, carreira.
  ```
- Cache resultado em `lead_natal_charts.interpretation_text`
- Quota Gemini consumida
- Output em markdown

### UX
- Tab "Mapa astral" → seção "Interpretação"
- Sub-perguntas: "Como vai meu amor?" / "E a carreira?" → re-prompt com foco
- Tarólogo pode editar texto antes de enviar pro lead

### Edge case
- Mapa incompleto (sem horário): interpretação foca em Sol+Lua, omite ascendente

---

## 4.7 Tarot virtual: deck digital

### Decks suportados
- Marselha (78 cartas, padrão)
- Rider-Waite (alternativa)
- Custom upload (Pro+): tarólogo sobe imagens próprias

### Assets
- 78 imagens PNG/SVG por deck (próprias ou licenciadas)
- Front + back (verso)
- Animação flip (CSS 3D transform)

### Data Model
```sql
CREATE TABLE tarot_decks (
  id VARCHAR(40) PRIMARY KEY,  -- "marselha", "rider", "tenant_xxx_custom"
  name VARCHAR(100),
  is_default BOOLEAN,
  tenant_id VARCHAR(64),  -- null se global
  created_at TIMESTAMP
);

CREATE TABLE tarot_cards (
  id VARCHAR(40),  -- "01_o_louco", "swords_2", etc
  deck_id VARCHAR(40) REFERENCES tarot_decks(id),
  name VARCHAR(100),
  arcana VARCHAR(10),  -- major|minor
  suit VARCHAR(20),    -- copas|ouros|espadas|paus (se minor)
  number INT,
  image_url VARCHAR(500),
  meaning_upright TEXT,
  meaning_reversed TEXT,
  keywords JSONB,
  PRIMARY KEY (id, deck_id)
);
```

### Seed
- Pre-load Marselha + Rider-Waite com significados curados (PT-BR)

---

## 4.8 Tarot virtual: simulador

### Spreads (modos de tiragem)
- 1 carta: "carta do dia"
- 3 cartas: passado / presente / futuro
- 5 cartas: cruz simples
- 10 cartas: cruz celta (Pro+)
- Custom (Enterprise): tarólogo monta layout

### UX
- Botão "🎴 Nova tiragem" no contexto do lead
- Modal: escolhe spread + foco da pergunta (amor/grana/saúde/geral)
- Animação shuffle deck
- Cartas viram uma por uma com transição
- Click carta → expande + significado + interpretação contextual

### Backend
- Random sampling sem reposição (78 sem repetir na mesma tiragem)
- Reverso: 30% chance por carta (config)
- Determinístico se opt-in: usa hash(lead_id + timestamp) como seed

---

## 4.9 Tarot virtual: leitura GPT contextual

### Backend
- Prompt:
  ```
  Você é uma tarot reader empática. Tirou estas 3 cartas pra Maria 
  (signo Touro, perguntou sobre amor):
  
  Passado: As Espadas (significado: ...)
  Presente: 3 de Copas (significado: ...)
  Futuro: O Sol (significado: ...)
  
  Faça uma leitura conectada, em pt-BR, max 250 palavras, tom acolhedor.
  Termine com 1 conselho prático.
  ```
- Output em markdown
- Cache de 5min por (lead, spread)

### UX
- Após tiragem, gera leitura inline
- Botão "Refresh" → nova interpretação
- Botão "Enviar pro lead" → manda como mensagem de áudio (voz clonada — 4.16) ou texto

### Edge cases
- Quota Gemini exceeded: fallback "interpretação genérica" (concatenando significados)

---

## 4.10 Tarot virtual: histórico

### Data Model
```sql
CREATE TABLE tarot_readings (
  id BIGSERIAL PRIMARY KEY,
  lead_id BIGINT REFERENCES leads(id),
  attended_by_user_id INT,
  spread_type VARCHAR(40),
  cards JSONB,  -- [{card_id, position, reversed}]
  question TEXT,
  interpretation TEXT,
  sent_to_lead BOOLEAN,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_readings_lead ON tarot_readings(lead_id, created_at DESC);
```

### UX
- Tab "Tiragens" no contexto do lead
- Lista cronológica + filtros
- Insights: "carta X aparece 3x — tema recorrente"

---

## 4.11 Numerologia: número da vida

### Cálculo
```python
def life_path_number(birth_date: date) -> int:
    digits = [int(d) for d in birth_date.strftime("%d%m%Y")]
    n = sum(digits)
    while n > 9 and n not in (11, 22, 33):  # mestre numbers
        n = sum(int(d) for d in str(n))
    return n
```

### Significados (1-9 + 11/22/33)
- Hardcoded em JSON

### UX
- Card "Numerologia" no contexto: "Número da vida: 7 — busca espiritual"
- Click → análise expandida

---

## 4.12 Numerologia: análise GPT

### Prompt
```
Maria tem número da vida 7. Faça análise numerológica empática
em pt-BR, max 150 palavras. Foque em propósito de vida + desafios.
```

---

## 4.13 Horóscopo diário automático

### Por quê
"Cada lead recebe horóscopo do seu signo às 7h da manhã, mantém engajamento."

### UX (admin)
- `/automations/daily-horoscope` — toggle on/off
- Config:
  - Horário envio (default 7h timezone do lead)
  - Source: "Gemini gera" / "API externa" / "Eu escrevo"
  - Segmentação: "todos os leads que aceitaram" / "só hot/warm" / etc
  - Opt-in: bot pergunta no onboarding "quer horóscopo diário?" → marca em `lead.consents.daily_horoscope`

### Backend
- Cron hourly: pra cada timezone, identifica leads cujo "agora" é o horário escolhido
- Gera 12 horóscopos (1 por signo) com Gemini ou puxa de API (theastrologer.io, etc)
- Envia broadcast → fila WhatsApp

### Data Model
```sql
CREATE TABLE daily_horoscopes (
  date DATE,
  zodiac_sign VARCHAR(20),
  text TEXT,
  source VARCHAR(40),
  generated_by VARCHAR(40),  -- gemini|api|manual
  PRIMARY KEY (date, zodiac_sign)
);
ALTER TABLE leads ADD COLUMN consents JSONB DEFAULT '{}';
-- consents: {daily_horoscope: true, marketing: false, ...}
```

### Edge cases
- Lead opt-out: para imediatamente
- Quota WhatsApp atingida: pula leads (não acumula)
- Horóscopo do dia já gerado: cache (não regenera por signo)

### Métricas
- `daily_horoscope.sent` {tenant_id, count}
- `daily_horoscope.opened` (proxy: lead respondeu nas próximas 4h)
- `daily_horoscope.opt_out`

---

## 4.14 Voice cloning ElevenLabs

### Por quê (KILLER FEATURE)
Tarólogo grava 1min de voz, sistema clona, **TODOS os áudios do bot saem na voz dela**. Lead pensa que ela respondeu pessoalmente. Conversão dispara.

### Provider
- **ElevenLabs**: melhor qualidade pt-BR, ~$22/mo enterprise
- Alternativas: Coqui TTS (open-source, hospedar próprio), OpenAI TTS

### Custo
- Embutido no Pro+ (incluso) e Enterprise
- Limite: ~10k caracteres/mês no Pro, ilimitado Enterprise

### Data Model
```sql
CREATE TABLE voice_clones (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  user_id INT,  -- dono da voz
  provider VARCHAR(40),  -- elevenlabs|coqui|openai
  provider_voice_id VARCHAR(100),
  enrollment_audio_url VARCHAR(500),
  status VARCHAR(20),  -- pending|active|failed
  consented_at TIMESTAMP,  -- LGPD
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Edge cases
- Múltiplos atendentes: cada member pode ter sua voz clonada (Enterprise)
- Voz banida (provider detectou clone abusivo): fallback texto
- Provider down: fallback TTS genérico

---

## 4.15 Voice cloning enrollment

### Fluxo (`/settings/voice`)
1. Card "Clone sua voz"
2. Botão "Começar gravação"
3. Modal: instrução "Leia este texto naturalmente em sua voz mais clara":
   ```
   "Olá, sou a Maria, sua tarot reader. Estou aqui pra te
   guiar na sua jornada espiritual. Cada carta tem um
   propósito, cada leitura é única..."  (1min de texto)
   ```
4. Mic enrollment 1min (waveform real-time)
5. Upload → ElevenLabs Voice Clone API
6. Status pending (~30s) → active
7. Botão "Testar voz" gera sample TTS

### Consent (LGPD)
- Checkbox obrigatório: "Autorizo Acássia a processar minha voz"
- Termo legal armazenado + assinatura digital (timestamp + IP)

### Edge cases
- Áudio muito curto/baixa qualidade: erro "grave em ambiente silencioso"
- Múltiplas pessoas falando: erro "só você deve falar"
- Idioma diferente: erro "deve ser pt-BR"

---

## 4.16 Audio messages na voz clonada

### UX
- Compose box: botão `🔊 áudio com IA`
- Modal: textarea "o que você quer falar?"
- Click "Gerar" → ElevenLabs TTS → preview
- Botão "Enviar" → manda como audio msg WhatsApp

### Backend
- Endpoint `POST /api/voice/synthesize {text, voice_clone_id}` → `{audio_url}`
- Salva em S3, retorna URL público (com expiry signed)
- Tracking: caracteres consumidos vs quota

### Auto-mode (no Builder)
- Nó "Áudio IA" — ao invés de texto, gera audio TTS automaticamente
- Permite emoção: tom calmo / energético / sussurrado

### Edge case
- Texto > 5000 chars: split em múltiplos áudios
- Provider failure: fallback texto + admin notificado

---

## 4.17 Audio library categorizada

### Por quê
Tarólogo pré-grava áudios genéricos pra reuso ("oração de proteção", "saudação manhã").

### UX (`/library/audio`)
- Grid de áudios:
  - Categorias: saudação, proteção, prosperidade, amor, fechamento, etc
  - Cada áudio: waveform + título + duração + tags
- Botão "+ Novo áudio" → upload ou gravar inline
- Click "▶️" → preview
- Botão "Enviar pro lead" → seleciona conversa
- Botão "Usar em fluxo" → vincula a nó de áudio

### Data Model
```sql
CREATE TABLE audio_library (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  title VARCHAR(200),
  category VARCHAR(40),
  tags JSONB,
  audio_url VARCHAR(500),
  duration_s INT,
  uploaded_by INT,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_audio_lib_tenant_cat ON audio_library(tenant_id, category);
```

### Smart suggestions (IA)
- Quando atendente está em conversa, painel sugere "áudio relevante: 'oração proteção'"

---

## 4.18 Stable Diffusion: aura espiritual

### Por quê
Visual diferenciado: "sua aura essa semana" → imagem gerada baseada em signo + leitura + lua atual.

### Provider
- Replicate.com (~$0.001/image) ou Together.ai
- Modelo: SDXL ou Flux

### Backend
- Prompt template:
  ```
  ethereal aura portrait of [color1] and [color2] energies, 
  mystical, spiritual, [zodiac_element] elements, dark background, 
  art nouveau style, glowing
  ```
- Cores derivadas do signo (Touro = verde+rosa, Leão = ouro+laranja, etc)
- Output 512×512

### UX
- Tab "Aura" no contexto do lead
- Botão "Gerar aura semanal"
- Imagem gerada em ~10s
- Botão "Enviar pro lead" → manda imagem WhatsApp

### Edge cases
- Provider down: skip silently
- Imagem inadequada (NSFW filter): regenera

---

## 4.19 Sentiment intent espiritual

### Categorias específicas
- amor / relacionamento
- dinheiro / prosperidade
- saúde
- carreira / trabalho
- família
- proteção / espiritualidade
- decisão / encruzilhada
- luto / perda

### Backend
- Classifier Gemini com prompt:
  ```
  Classifique a mensagem em 1+ categorias: amor, dinheiro, saúde, ...
  Mensagem: "preciso saber se ele vai voltar"
  Output JSON: {categories: ["amor"], urgency: "high", emotion: "ansiedade"}
  ```
- Persiste em `mensagens.spiritual_intent`

### Uso
- Filtro de fila: "só leads de amor"
- Roteamento: leads de luto → atendente especializado
- Persona adapta: "vejo que você quer falar sobre amor..."

---

## 4.20 Specialized prompts

### Personas pré-construídas
1. **Cigana mística** — linguagem mais popular, "minha rainha", referências ciganas
2. **Tarot reader literária** — vocabulário rico, citações
3. **Espírita acolhedora** — referências a Chico Xavier, doutrina espírita
4. **Astróloga moderna** — científica + intuitiva
5. **Reiki/holística** — chakras, energias
6. **Umbanda/Candomblé** — entidades, terreiro (cuidado: não apropriação)

### Backend
- Cada persona: system prompt completo + glossário + tom + exemplos few-shot
- User escolhe no Studio → customiza por cima

### Edge case
- Cuidado cultural: avisar tarólogo em personas religiosas afro-brasileiras

---

## 4.21 Glossário espiritual no GPT

### Por quê
GPT às vezes erra termos: confunde "egum" com "água", troca cartas. Glossário força acerto.

### Implementação
- Tabela `tenant_spiritual_glossary` com termos + definições + uso correto
- Injetado no system prompt:
  ```
  Termos importantes:
  - "Trono" = guia espiritual elevado
  - "Pomba-gira" = entidade feminina, tratada com respeito
  - ...
  ```

### Data Model
```sql
CREATE TABLE spiritual_glossary (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  term VARCHAR(100),
  definition TEXT,
  usage_examples JSONB,
  is_global BOOLEAN DEFAULT FALSE
);
```

### UX
- `/library/glossary` — CRUD termos
- Pre-seed com 100+ termos do português místico

---

## 4.22 Calendário de ritos/datas espirituais

### Datas importantes
- Equinócios e solstícios
- Páscoa (cristã)
- Datas de orixás (Iemanjá 2/2, Cosme&Damião 27/9, etc)
- Datas pagãs (Samhain, Beltane)
- Lua nova/cheia
- Eclipses

### UX (`/calendar`)
- Combina lunar + ritos + eventos custom
- Toggle: tradições visíveis (cristã, afro, pagã, oriental)
- Click data → "tradição X celebra Y — sugestões de mensagem"

### Data Model
```sql
CREATE TABLE spiritual_dates (
  date DATE,
  tradition VARCHAR(40),
  name VARCHAR(200),
  description TEXT,
  recurring VARCHAR(20),  -- annual|lunar|fixed
  PRIMARY KEY (date, tradition)
);
```

---

## 4.23 Onboarding kit "monte sua tarot card"

### Por quê
Novos tarólogos não sabem por onde começar. Kit pronto = 5min até primeiro fluxo.

### UX (durante onboarding ou `/onboarding-kits`)
- Galeria de templates:
  - "Tarô do Amor Express" — funil 5 nós, 67BRL
  - "Mistério Reservado" — funil 7 nós, 197BRL
  - "Mapa Astral Completo" — funil 4 nós, 97BRL
  - "Sessão Online" — agendamento + pagamento
- Click → preview interativo do fluxo + samples de copy
- Botão "Aplicar" → clona pra workspace + vai pro Builder

### Backend
- Templates como blueprints exportados em JSON
- Tabela `flow_kits` com metadata + JSON do fluxo

---

## 4.24 Comunidade/grupos espirituais

### Conceito (Pro+)
- WhatsApp Group automation: tarólogo cria grupo "Círculo da Lua Cheia", bot envia conteúdo automaticamente
- Pra leads VIP: grupo exclusivo com tiragens semanais

### Implementação
- Meta WhatsApp Cloud API suporta grupos via Group ID
- Bot manda mensagens broadcast no grupo (não individual)
- Membros entram via link → bot reconhece (se phone está em leads)

---

## 4.25 Capture data nascimento via WA natural

### Por quê
Tem que ser natural — não formulário rígido. Lead odeia formulário no WhatsApp.

### Fluxo conversacional
- Bot: "Pra fazer sua leitura, preciso saber quando você nasceu — pode me contar?"
- Lead: "23 de maio de 1986"
- Bot Gemini parser:
  ```
  Extract birth date from: "23 de maio de 1986"
  → {date: "1986-05-23", confidence: 0.95}
  ```
- Confirma: "23/05/1986, certo?" → lead confirma → persiste

### Edge cases
- "Maio de 86" (sem dia): pergunta "que dia exatamente?"
- "Não lembro" (raro): aceita só ano + signo aproximado
- Data inválida (29/02 não-bissexto): pergunta "checa por favor"

---

## 4.26 Smart greeting baseado em fase lunar/signo

### Por quê
"Bom dia, Maria!" é genérico. "Bom dia, querida Maria, hoje a lua está em Câncer..." é poético.

### Implementação
- Variável `{{smart_greeting}}` em qualquer template
- Backend gera dinamicamente:
  ```python
  def smart_greeting(lead) -> str:
      time_of_day = ...  # bom dia/tarde/noite
      lunar = lunar_today()
      sign = lead.signo
      return personalize(f"{time_of_day}, querida {lead.name}, "
                         f"hoje a lua está em {lunar.zodiac} "
                         f"e ela ressoa especial pra você de {sign}...")
  ```

---

## 4.27 "Mensagem do dia" personalizada

### Por quê
Cada lead recebe um insight diário único.

### Backend
- Cron diário gera msg personalizada por lead (Pro+):
  ```
  Maria, [signo], [fase lunar], últimas tendências do mapa astral:
  → mensagem motivacional + insight específico
  ```
- Quota Gemini: ~$0.001 por msg

### UX
- Opt-in via bot na onboarding
- Tarólogo vê dashboard "X mensagens enviadas hoje"

---

## 4.28 Tiragem agendada

### UX
- "Quero tiragem na próxima lua cheia"
- Bot: "Próxima lua cheia: 12/05. Agendado!"
- 1h antes da lua cheia: bot manda "preparando sua tiragem..."
- Hora certa: tiragem rolá automática + leitura

### Data Model
```sql
CREATE TABLE scheduled_readings (
  id BIGSERIAL PRIMARY KEY,
  lead_id BIGINT,
  scheduled_for TIMESTAMP,
  trigger_type VARCHAR(40),  -- lunar_full|date|sign_transit
  spread_type VARCHAR(40),
  status VARCHAR(20),  -- pending|sent|cancelled
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4.29 Card draw history + tendências

### UX (lead context)
- Gráfico das cartas mais frequentes nas tiragens daquele lead
- "A carta da Estrela apareceu 5x — tema recorrente"
- Insight de tendências: "do passado triste pro futuro luminoso"

---

## 4.30 Acessibilidade espiritual (voice-only mode)

### Por quê
Muitos leads idosos / com baixa alfabetização preferem áudio. App em modo "só áudio" pra tarólogo + lead.

### Modo
- Toggle "modo áudio" no Inbox
- Compose só permite gravação de áudio (não texto)
- Mensagens recebidas: TTS auto-play

---

## Resumo executivo Frente 4

### Tabelas novas (12)
1. `lunar_phases`
2. `lunar_triggers`
3. `lead_natal_charts`
4. `tarot_decks` + `tarot_cards`
5. `tarot_readings`
6. `daily_horoscopes`
7. `voice_clones`
8. `audio_library`
9. `spiritual_glossary`
10. `spiritual_dates`
11. `flow_kits`
12. `scheduled_readings`

### Alterações em existentes
- `leads`: `birth_date`, `birth_time`, `birth_place`, `birth_lat/lon`, `signo`, `ascendente`, `lua`, `consents`
- `mensagens`: `spiritual_intent`

### Bibliotecas Python novas
- `pyswisseph` (mapas astrais, lunar)
- `geopy` (geocoding)

### Provider integrations
- ElevenLabs (voice cloning) — Pro+
- Replicate (Stable Diffusion) — opcional Pro+
- API horóscopo (theastrologer.io) — fallback

### Endpoints novos: ~25 sob `/api/lunar/*`, `/api/astrology/*`, `/api/tarot/*`, `/api/voice/*`, `/api/library/*`

### Frontend
- `/calendar/lunar`, `/library/audio`, `/library/glossary`, `/settings/voice`, `/onboarding-kits`
- Tab "Mapa astral" / "Tiragens" / "Aura" no contexto do lead
- Componentes: TarotSpread, NatalChart (SVG), VoiceEnrollment

### Sprints sugeridos
- **A (sem 1-3)**: 4.1, 4.2, 4.3, 4.7, 4.8, 4.9, 4.14, 4.15, 4.16, 4.20 — core killer features (voice + tarô + signo + lunar trigger)
- **B (sem 4-5)**: 4.4, 4.5, 4.6, 4.10, 4.11, 4.12, 4.13, 4.17, 4.19, 4.21, 4.25, 4.26 — completar suite espiritual
- **C (sem 6-7)**: 4.18, 4.22, 4.23, 4.27, 4.28, 4.29 — diferenciação extra
- **D (sem 8+)**: 4.24, 4.30 — power features
