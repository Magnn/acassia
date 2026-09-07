# Spec Acássia 360° — Frente 5: UX da Plataforma

> Polimento de produto. O que faz tarólogo abrir a plataforma todo dia em vez de só usar quando precisa.
>
> Status: 📝 spec aprovada, 🚧 implementação não iniciada.
> Última atualização: 2026-04-29

## Inventário

| #    | Feature                                             | Crítico? | Sprint |
|------|-----------------------------------------------------|----------|--------|
| 5.1  | Onboarding gamificado (checklist + confete)        | 🔴 sim   | A      |
| 5.2  | First message goal (5 minutos)                      | 🔴 sim   | A      |
| 5.3  | Pre-built funnel templates                          | 🔴 sim   | A      |
| 5.4  | Persona generator AI                                | 🟡 alto  | B      |
| 5.5  | Live preview de WhatsApp no Builder                 | 🔴 sim   | A      |
| 5.6  | Test simulator com personas                         | 🟡 alto  | B      |
| 5.7  | Cmd+K palette global                                | 🔴 sim   | A      |
| 5.8  | Mobile PWA installable                              | 🔴 sim   | B      |
| 5.9  | Push notifications                                  | 🔴 sim   | B      |
| 5.10 | Voice memo to flow                                  | 🟢 médio | D      |
| 5.11 | Empty states orientadas                             | 🟡 alto  | A      |
| 5.12 | Loading states craftadas                            | 🟡 alto  | A      |
| 5.13 | Tour guiado in-app (Shepherd / Driver.js)           | 🟡 alto  | B      |
| 5.14 | Help center embedded                                | 🟢 médio | C      |
| 5.15 | Changelog in-app                                    | 🟢 médio | C      |
| 5.16 | Dark mode polish                                    | 🟡 alto  | B      |
| 5.17 | Theming presets (4 paletas)                         | 🟢 médio | C      |
| 5.18 | Atalhos de produto (toolbar fixo)                   | 🟢 médio | C      |
| 5.19 | Dashboard customizável (drag widgets)               | 🟢 médio | C      |
| 5.20 | Mobile inspector                                    | 🟡 alto  | B      |
| 5.21 | Acessibilidade (a11y completa)                      | 🔴 sim*  | B      |
| 5.22 | i18n (preparação multi-idioma)                      | 🟢 médio | D      |
| 5.23 | Performance budgets                                 | 🟡 alto  | B      |
| 5.24 | Search inline em listas                             | 🟡 alto  | B      |
| 5.25 | Bulk operations consistente                         | 🟡 alto  | B      |
| 5.26 | Toast queue + notification center                   | 🟡 alto  | A      |
| 5.27 | Skeleton loading consistente                        | 🟡 alto  | A      |
| 5.28 | Confirmação destrutiva (modal padrão)               | 🔴 sim   | A      |
| 5.29 | Undo last action (toast com revert)                 | 🟢 médio | C      |
| 5.30 | Keyboard navigation completa                        | 🟡 alto  | B      |
| 5.31 | Print-friendly views (relatórios)                   | 🟢 médio | D      |
| 5.32 | Breadcrumbs consistentes                            | 🟢 médio | C      |
| 5.33 | Quick actions FAB (mobile)                          | 🟡 alto  | B      |
| 5.34 | Onboarding sub-products (per-tela primeira vez)     | 🟡 alto  | C      |

\* a11y: legal em alguns mercados, lei brasileira ainda permissiva

---

## 5.1 Onboarding gamificado

### Por quê
Onboarding hoje é wizard linear — é OK mas não engaja. Gamificação aumenta completion 30%+.

### Conceito
Checklist sticky de 5-7 milestones, cada completion = confete + badge + progresso visual.

### Milestones (ordem)
1. ✅ Persona criada
2. ✅ WhatsApp conectado
3. ✅ Primeiro fluxo publicado
4. ✅ Primeira mensagem enviada
5. ✅ Primeiro lead captado
6. ✅ Primeira venda registrada
7. ✅ Convidar primeiro membro / configurar tema

### UX
- **Sidebar persistente** (durante primeira semana): "Conquistas — 3/7 completas"
- **Click**: expande lista
- **Item completo**: checkmark verde + animação
- **Em progresso**: spinner + "agora..."
- **Próximo**: destaque + CTA "fazer agora"
- **Tudo completo**: card final "🎉 Bem-vinda à Acássia! [fechar checklist]"

### Confete + sounds
- Item completado: confetti.js animation curta + som opcional
- Conquista final: animação maior + email "parabéns, você é um power user"

### Data Model
```sql
CREATE TABLE onboarding_milestones (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  milestone_key VARCHAR(40),  -- persona_created|whatsapp_connected|...
  completed_at TIMESTAMP,
  PRIMARY KEY (user_id, milestone_key)
);
```

### Backend
- Each app event triggers check: "completou milestone X?" → marca + emite event
- Frontend invalida query → checklist atualiza

### Edge cases
- Milestone refeito (re-conectou WA): não reganha confete
- User pula etapa: marca como pulado, badge fica grey
- 30d sem completar tudo: nudge email "falta pouco — termina seu setup"

### Métricas
- `onboarding.milestone_completed` {key, time_since_signup_h}
- `onboarding.checklist_dismissed`
- Funnel: milestone 1 → 2 → 3 → ... → 7 (target: 70% completam 1-3, 40% completam 1-7)

---

## 5.2 First message goal (5 minutos)

### Por quê
Time-to-value (TTV) crítico. Tarólogo precisa enviar primeira mensagem em ≤ 5min do signup pra ficar "fisgado".

### Fluxo express (alternativa ao wizard padrão)
- Tela imediatamente após signup: "Vamos enviar tua primeira mensagem em 5 minutos?"
- Botão "Sim, modo express"
- 4 mini-passos:
  1. **Conecte teu WhatsApp** — só QR code (Evolution se Meta não disponível)
  2. **Escolhe um template** — galeria 3 cartões "Tarô do Amor / Mistério / Mapa Astral"
  3. **Personalizar** (opcional) — apenas nome do funil + 1 valor (oferta)
  4. **Mandar pra você mesma** — "qual seu número WhatsApp pessoal?" → bot manda fluxo de teste pra ela

### UX feedback
- Timer top: "00:42" contando upward (não pressão, gamification)
- Cada passo completo: micro-confete
- Final: "🎉 Você fez em 4:23 — seu primeiro fluxo está vivo!"

### Métricas
- `express_onboarding.started`
- `express_onboarding.completed` {duration_s}
- `express_onboarding.abandoned` {step}
- Target: 60% completam, mediana < 8min

---

## 5.3 Pre-built funnel templates

### Por quê
Tarólogo iniciante não sabe estruturar funil. Template pronto = setup em 2 cliques.

### Templates inclusos (V1)
1. **Tarô do Amor Express** (R$67)
   - Saudação → Coleta nome+pergunta → Sugestão de tiragem → Oferta R$67 → Pix → Áudio leitura
2. **Mistério Reservado** (R$197)
   - Saudação warm → Coleta dados profundos → Engajamento 3 msgs → Oferta R$197 → Bonus exclusivo
3. **Mapa Astral Completo** (R$97)
   - Captura nascimento → Mapa visual preview → Oferta análise completa
4. **Sessão Online 1:1** (R$300)
   - Triagem qualificação → Agendamento Cal.com → Pagamento upfront
5. **Reativação de leads** (recovery)
   - Mensagem reengajamento → Oferta com desconto → Win-back

### UX (`/templates`)
- Galeria de cards:
  - Imagem mockup + nome + descrição curta
  - Tags: nicho, ticket médio, complexidade
  - Métrica: "usado por X tarólogos"
  - Preview interativo: hover → simula conversa
- Click "Aplicar template":
  - Modal: "Esse template vai criar fluxo, agente e templates de mensagem. Continuar?"
  - Aplicar → clona tudo pra workspace + abre Builder

### Data Model
```sql
CREATE TABLE flow_templates (
  id VARCHAR(40) PRIMARY KEY,
  name VARCHAR(200),
  description TEXT,
  category VARCHAR(40),
  preview_image_url VARCHAR(500),
  ticket_brl_avg INT,
  blueprint_json JSONB,
  agent_json JSONB,
  usage_count INT DEFAULT 0,
  is_official BOOLEAN DEFAULT TRUE,
  created_by_admin_id INT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Backend
- `POST /api/templates/<id>/apply` → cria flow + agent + templates_msg + retorna IDs

### Marketplace expansion (Frente 7.14)
- Tarólogos pro+ podem publicar próprios templates pra outros (revenue share)

### Métricas
- `template.previewed`
- `template.applied` {template_id}

---

## 5.4 Persona generator AI

### Por quê
Tarólogo não sabe descrever sua "voz" pro bot. IA gera baseada em poucas perguntas.

### UX (no onboarding)
- Tela: "Como sua bot deve falar com leads?"
- 5 perguntas curtas (sliders + multiple choice):
  1. Tom: ⚪ formal — ⚪○⚪ casual — ⚪ místico
  2. Energia: ⚪ calma — ⚪⚪⚪ energética — ⚪ poética
  3. Emojis: ❌ nenhum — ⚪⚪⚪ moderado — ⚪ muitos
  4. Comprimento: ⚪ curto — ⚪⚪⚪ médio — ⚪ longo
  5. Especialidade: amor / dinheiro / proteção / espiritualidade / geral
- Click "Gerar minha persona" → Gemini gera:
  - Nome sugerido
  - Apresentação 2 linhas
  - Saudação template
  - Estilo de leitura
- User edita ou aceita → persiste no agente

### Backend
- Prompt template já definido
- Output JSON estruturado pra mapear nos campos

### Edge case
- User não satisfeito → botão "Tentar de novo" gera variação
- 3 tentativas: sugere intervenção manual

---

## 5.5 Live preview de WhatsApp no Builder

### Por quê
Builder hoje é canvas abstrato. Tarólogo não visualiza como vai sair na prática.

### UX
- Painel direito do Builder (toggle): "Preview WhatsApp"
- Mockup celular vertical com tela de chat
- Conforme você seleciona/edita um nó: preview atualiza mostrando msgs renderizadas
- Toggle "Persona test": escolhe Maria/João/Ana, preview simula conversa real (clicando "próx" avança nó)

### Implementação
- Componente React `WhatsAppMockup` (SVG/CSS detalhado)
- Estado: array de msgs com sender (bot/user)
- Personas: pré-definidas com respostas mock pra cada nó

### Edge case
- Nós dinâmicos (com IA): preview usa "[resposta IA]" placeholder
- Mídia: mostra placeholder visual, não baixa real

---

## 5.6 Test simulator com personas

### Sub-feature de 5.5
- 5 personas pré-construídas:
  - Maria, 45, viúva, busca amor — respostas curtas, emocional
  - João, 35, empreendedor — pragmático, foco grana
  - Ana, 28, ansiosa — pergunta muito, hesitante
  - Pedro, 60, religioso — cético com tarô, abre devagar
  - Custom — user define respostas
- Cada persona testa fluxo de ponta a ponta
- Métrica: "essa persona dropou no nó 3 — drop alto?"

---

## 5.7 Cmd+K palette global

### Por quê
Atalho universal de produtividade (Linear, Notion, Vercel).

### UX
- `Cmd+K` (Mac) ou `Ctrl+K` (Win) em qualquer página → modal centralizado
- Search input + lista resultados agrupada:
  - **Ações**: "criar fluxo", "novo lead", "ir pra dashboard"
  - **Navegação**: links pra todas rotas
  - **Leads**: top 5 matches por nome/phone
  - **Fluxos**: top 5 matches
  - **Configurações**: "configurar WhatsApp", "convidar membro"
  - **Documentação**: artigos do help center
- ↑↓ navega, Enter executa
- Atalhos visíveis (`Esc` fecha, `Cmd+Enter` ação primária)

### Backend
- Index local (commands estáticos) + busca remota (leads/flows) com debounce 200ms
- Cache 5min de buscas frequentes

### Customização
- "Recent": últimas 5 ações do user no topo
- "Favorites": user pina ações favoritas

---

## 5.8 Mobile PWA installable

### Por quê
Tarólogo não fica em frente ao computador. Precisa atender lead enquanto na rua.

### Implementação
- `manifest.json` com:
  ```json
  {
    "name": "Acássia",
    "short_name": "Acássia",
    "icons": [{"src": "/icon-192.png", "sizes": "192x192"}, {"src": "/icon-512.png", "sizes": "512x512"}],
    "start_url": "/dashboard",
    "display": "standalone",
    "background_color": "#1a1a1a",
    "theme_color": "#9333ea",
    "orientation": "portrait"
  }
  ```
- Service worker (Workbox):
  - Cache shell estático (CSS/JS)
  - Network-first pra API
  - Background sync pra mensagens enviadas offline
- Install prompt: aparece após 3 visitas + dismiss-able

### UX mobile-first
- Inbox 3-painel vira **stack** com swipe entre telas
- Bottom nav: Inbox / Dashboard / Builder / Mais
- Floating action button (FAB) "+ Nova mensagem"

### Edge cases
- iOS: PWA limitado (sem push real até iOS 16.4+)
- Tela travada com keyboard aberto: gerencia viewport

---

## 5.9 Push notifications

### Tipos (mesma lista de Frente 3.42)
- Nova msg inbound em lead atribuído
- @mention em nota
- SLA breached
- Trial expirando
- Quota crítica

### Implementação
- Web Push API + Service Worker
- VAPID keys self-hosted
- Backend envia via `pywebpush`

### UX
- Permission prompt no primeiro signup ou ação relevante (não no carregamento — UX ruim)
- Settings `/notifications`:
  - Toggle por tipo
  - "Modo silencioso" (não recebe nada entre 22h-7h)

### Data Model
```sql
CREATE TABLE push_subscriptions (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  endpoint VARCHAR(500),
  p256dh VARCHAR(200),
  auth VARCHAR(200),
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  last_used_at TIMESTAMP
);
```

### Edge cases
- Subscription invalidada (user limpou cache): backend remove
- iOS Safari: requires PWA installed first

---

## 5.10 Voice memo to flow

### Por quê
"Maria grava áudio descrevendo o fluxo que quer, IA cria estrutura."

### UX (`/builder/from-voice`)
- Botão grava áudio
- Lead grava 1-3 min descrevendo: "Quero um fluxo de tarô amor que pergunta nome, signo, oferece tiragem por 67 reais, manda áudio com leitura..."
- Backend: Whisper transcreve + Gemini estrutura em blueprint JSON
- Preview do fluxo gerado → user revisa → publica

### Edge cases
- Áudio confuso: bot pergunta perguntas de clarificação
- Estrutura inválida: IA tenta corrigir, senão mostra erro

---

## 5.11 Empty states orientadas

### Por quê
"Você não tem leads ainda" não ajuda. Tem que ensinar.

### Templates de empty state
- **Sem leads**: ilustração + "Vamos pegar seus primeiros leads? Compartilhe esse link na sua bio: [link]"
- **Sem fluxos**: "Crie seu primeiro fluxo em 2 cliques: [Aplicar template] [Builder vazio]"
- **Sem WhatsApp conectado**: "Conecte seu WhatsApp pra começar: [Conectar agora]"
- **Inbox vazio**: "Tudo limpo! Bom trabalho. Próximo lead aparecerá aqui."
- **Sem analytics dados**: "Aguardando primeiros leads. Você pode testar com [link de simulação]"

### Componente padrão
```tsx
<EmptyState
  icon={...}
  title="Sem leads ainda"
  description="..."
  cta={{label: "Compartilhar link", onClick: ...}}
  illustration="empty-leads.svg"
/>
```

---

## 5.12 Loading states craftadas

### Tipos
- **Skeleton**: pra listas/tabelas (linhas placeholder com shimmer)
- **Spinner**: pra ações curtas (<2s)
- **Progress bar**: pra uploads/longos (>2s)
- **Optimistic UI**: pra ações comuns (toggle, like)

### Padrão
- Sempre algo na tela (nunca flash branco)
- Skeleton match exato do layout final (mesmo height)
- Mensagem dinâmica em ações longas: "Conectando ao WhatsApp..." → "Aguardando QR code..."

---

## 5.13 Tour guiado in-app

### Lib
- Driver.js ou Shepherd.js

### Tours
- **First Login Tour**: 5 passos — sidebar nav, dashboard, inbox, builder, settings
- **Builder Tour**: ao abrir Builder primeira vez — paleta, canvas, inspector
- **Inbox Tour**: 3-painel + atalhos
- **Pré-publicar**: tour ao publicar primeiro fluxo (alerta importante)

### UX
- Spotlight em elemento + tooltip explicativo
- "Próximo" / "Pular tour" / "Não mostrar mais"
- Persisted: user que completou não vê de novo

### Data Model
```sql
ALTER TABLE users ADD COLUMN tours_completed JSONB DEFAULT '[]';
```

---

## 5.14 Help center embedded

### Conteúdo
- Artigos curtos por tópico (50+ inicial)
- Vídeos curtos (Loom-style)
- FAQ
- Glossário Acássia

### UX
- Botão help fixo bottom-right `?`
- Click → drawer com:
  - Search artigos
  - "Sugeridos pra essa página" (context-aware)
  - "Falar com suporte" (Pro+ priority)
- Inline help: ícone `(?)` em campos complexos → tooltip rich

### Backend
- Conteúdo em CMS leve (Notion API ou self-hosted markdown)
- ou: Crisp/Intercom embedded

---

## 5.15 Changelog in-app

### Por quê
"Lançamos voice cloning!" — user precisa saber sem checar email.

### UX
- Sino 🔔 com badge "novo" piscando
- Click → drawer "Novidades":
  - Lista cronológica de releases
  - Cada item: título, descrição curta, GIF/screenshot, "saiba mais"
- Marcar como lido auto após visualizar

### Backend
- Tabela `changelog_entries` admin CRUD
- API `GET /api/changelog/recent` retorna últimos 10
- `users.last_changelog_seen_at` rastreia

---

## 5.16 Dark mode polish

### Por quê
Hoje tem dark mode mas é meio cru. Polir.

### Trabalho
- Auditoria visual: cada componente em ambos modos
- Contraste WCAG AA (mínimo 4.5:1)
- Cores semânticas consistentes:
  - `bg-primary`, `bg-surface`, `bg-elevated` (3 níveis)
  - `text-primary`, `text-secondary`, `text-disabled`
  - `accent-amethyst`, `accent-rose`, `accent-success`, `accent-warning`, `accent-danger`
- Imagens: invertidas vs preservadas (logos)
- Code highlighting (se aplicável): theme dark-friendly

### Toggle
- 3 modos: light / dark / system (default system)
- Persisted user preference
- Animação suave na troca (300ms)

---

## 5.17 Theming presets

### Por quê
Algumas tarólogas querem visual mais "feminino místico", outras mais "minimalista profissional".

### Presets
1. **Noite Considerada** (atual default — roxo/preto)
2. **Aurora** (rosa pastel + dourado, light)
3. **Floresta Encantada** (verde escuro + bege)
4. **Sangue da Lua** (vermelho profundo + preto)

### UX
- `/settings/appearance` → preview cards
- Click preset → aplica em todo app
- Custom (Pro+): scheme picker

### Implementação
- CSS variables organizadas
- Cada preset é um set de overrides

---

## 5.18 Atalhos de produto (toolbar fixo)

### Por quê
Ações comuns precisam estar 1 clique de qualquer tela.

### UX
- Toolbar fixo top-right (após avatar):
  - 🔔 Notificações
  - ⚡ Quick actions (dropdown: novo lead, novo fluxo, broadcast, etc)
  - ❓ Help
  - 👤 User menu

---

## 5.19 Dashboard customizável

### Por quê
Cada user tem prioridades diferentes. Dashboard fixo não serve todo mundo.

### UX (`/dashboard`)
- Modo "edição" → drag-drop widgets
- Lista de widgets disponíveis:
  - Cota usage
  - Top leads hot
  - Funnel quick view
  - Chart MRR (se tem vendas)
  - Recovery suggestions
  - Calendar lunar
  - Latest changelog
  - Quick actions
- Layout grid (react-grid-layout)
- Persisted por user

### Data Model
```sql
ALTER TABLE users ADD COLUMN dashboard_layout JSONB;
-- {widgets: [{id, x, y, w, h}, ...]}
```

---

## 5.20 Mobile inspector

### Por quê
Builder no mobile parece broken — inspector lateral some. Refazer pra mobile.

### UX mobile
- Tap nó no canvas → bottom sheet com inspector
- Drag handle pra expandir/colapsar
- Inputs grandes (touch-friendly)
- Save explícito (não autosave em mobile pra economizar bateria)

---

## 5.21 Acessibilidade (a11y)

### Padrões
- WCAG 2.1 AA mínimo
- Keyboard navigation completa
- ARIA labels em todos elementos interativos
- Focus management (modal fecha → foco volta)
- Screen reader testado (NVDA, JAWS, VoiceOver)
- Color blindness: não dependo só de cor (usa ícone + texto)

### Auditoria contínua
- axe-core in CI
- Lighthouse a11y score > 90

### Funcionalidades
- "Reduzir movimento" (respeita `prefers-reduced-motion`)
- High contrast mode
- Tamanho de fonte: 100/125/150% toggle

---

## 5.22 i18n (preparação multi-idioma)

### Por quê
Hoje pt-BR. Eventualmente: pt-PT, es-AR, es-MX, en-US.

### Trabalho preparatório (V1: só estrutura)
- Migrar strings hardcoded → JSON files (`pt-BR.json`, `en.json`)
- React-i18next ou Lingui
- Detectar locale do browser
- Fallback chain

### Não-string content
- Datas: format por locale
- Números: separadores
- Currency: BRL → USD/EUR

### Não no V1
- Conteúdo gerado por IA (Gemini suporta multi-idioma nativo)
- Personas culturais (precisa adaptar — fase 2)

---

## 5.23 Performance budgets

### Métricas-alvo
- **LCP** < 2.5s
- **FID** < 100ms
- **CLS** < 0.1
- **TTI** < 5s
- **Bundle JS inicial** < 250KB (gzip)
- **API p99** < 500ms

### Ferramentas
- Lighthouse CI (PR check bloqueia se regredir)
- Sentry Performance
- Web Vitals tracking telemetria

### Otimizações
- Code splitting agressivo (já tem lazy)
- Image optimization (WebP + lazy load)
- Tree shaking
- Defer não-crítico
- Edge caching estático

---

## 5.24 Search inline em listas

### Por quê
Toda lista grande precisa de search. Hoje só algumas têm.

### Padrão
- Input top da lista com `🔍`
- Atalho `/` foca
- Debounce 200ms
- Highlights matches
- "X resultados de Y" + "limpar"

### Coberto em
- Inbox queue (3.5)
- Tenant grid (1.3)
- Adicionar em: leads, flows, agents, templates, library audio, etc.

---

## 5.25 Bulk operations consistente

### Padrão
- Checkbox na primeira coluna
- "Selecionar página" no header
- "Selecionar todos os X" link após selecionar visíveis
- Bulk action bar aparece quando ≥1 selecionado
- Ações: tag, delete, export, mover, etc

### Confirmação
- < 10 itens: ação imediata + toast
- 10-100: modal "tem certeza? X itens"
- > 100: modal extra confirmação + queue + email pós-fato

---

## 5.26 Toast queue + notification center

### Toast
- Bibliotec: react-hot-toast ou sonner
- Tipos: success (verde), error (vermelho), warning (amarelo), info (azul), loading (cinza)
- Stack: max 3 visíveis, fila esperando
- Auto-dismiss: 4s success, 6s warning, 8s error
- Hover pausa
- Click descarta

### Notification center
- Sino 🔔 acumula notificações persistentes (não toast)
- Badge contador unread

---

## 5.27 Skeleton loading consistente

### Padrão
- Skeleton match exato do layout final
- Animação shimmer
- Componentes:
  - `<Skeleton width="100" height="20" />`
  - `<SkeletonCard />` (pre-built tipos)
  - `<SkeletonTable rows={5} cols={4} />`

---

## 5.28 Confirmação destrutiva (modal padrão)

### Por quê
Usuário deletando lead por engano = perda inaceitável. Modal padrão protege.

### UX
- Componente `<DestructiveConfirm>`:
  - Título "Você tem certeza?"
  - Descrição "Essa ação não pode ser desfeita. Você vai perder X."
  - Confirmação extra: digitar "DELETAR" pra liberar botão
  - Botão vermelho "Sim, deletar"
  - Botão neutro "Cancelar" (focus default)

### Onde aplicar
- Deletar lead, fluxo, agente, template, tenant
- Cancelar assinatura
- Hard delete

---

## 5.29 Undo last action

### Por quê
"Acabei de fechar lead errado" → undo em 5s salva o dia.

### UX
- Após ação destrutiva, toast com "Lead X fechado [Desfazer]"
- 5s de janela
- Click "Desfazer" → reverte

### Implementação
- Frontend mantém last action + revert callback
- Backend: ações reversíveis marcadas com flag `is_undoable`

---

## 5.30 Keyboard navigation completa

### Padrão
- `Tab` navega elementos
- `Enter` ativa primário
- `Esc` fecha modais
- Listas: ↑↓ navega, Enter abre
- Tabs: `Cmd+1`..`9` switch

### Auditoria
- Toda página testável só com teclado

---

## 5.31 Print-friendly views

### Por quê
Tarólogos querem imprimir relatórios pra contadora.

### Páginas com print
- Usage report
- Faturamento history
- Lead export

### CSS
- `@media print` esconde nav + sidebar, expande conteúdo
- Tabelas com headers repetindo
- Cores → escala de cinza

---

## 5.32 Breadcrumbs consistentes

### UX
- Header de cada página: "Dashboard > Leads > Maria Silva"
- Click cada nível navega
- Mobile: só último + back arrow

---

## 5.33 Quick actions FAB (mobile)

### Por quê
Em mobile, sem teclado, ações precisam ser 1 tap.

### UX
- Floating Action Button bottom-right
- Tap → menu radial:
  - 📩 Nova mensagem
  - ➕ Novo lead manual
  - 🎴 Tiragem rápida
  - 🔊 Áudio rápido

---

## 5.34 Onboarding sub-products

### Por quê
Tela "Builder" primeira vez é overwhelming. Mini-tour específico ajuda.

### Tours por feature
- Builder primeira vez: 4 passos
- Studio primeira vez: 3 passos
- Inbox primeira vez: 5 passos
- Mapa astral primeira vez: 2 passos

---

## Resumo executivo Frente 5

### Tabelas novas (5)
1. `onboarding_milestones`
2. `flow_templates`
3. `push_subscriptions`
4. `changelog_entries`
5. `tours_completed` (na users)

### Alterações em users
- `dashboard_layout`, `tours_completed`, `last_changelog_seen_at`, `theme_preset`

### Bibliotecas frontend novas
- `react-hot-toast` ou `sonner` (toast)
- `driver.js` ou `shepherd.js` (tour)
- `react-grid-layout` (dashboard)
- `confetti.js` (gamification)
- `i18next` (preparação i18n)
- `workbox` (PWA service worker)

### Endpoints novos: ~15

### Frontend
- `<EmptyState>`, `<DestructiveConfirm>`, `<Skeleton>`, `<Toast>` componentes
- Cmd+K palette
- Dashboard customizable
- Mobile bottom nav + FAB
- Tour overlays
- Help center drawer

### Sprints
- **A (sem 1-2)**: 5.1, 5.2, 5.3, 5.5, 5.7, 5.11, 5.12, 5.26, 5.27, 5.28 — onboarding + UX foundation
- **B (sem 3-4)**: 5.4, 5.6, 5.8, 5.9, 5.13, 5.16, 5.20, 5.21, 5.23, 5.24, 5.25, 5.30, 5.33 — mobile + a11y + polish
- **C (sem 5-6)**: 5.14, 5.15, 5.17, 5.18, 5.19, 5.29, 5.32, 5.34
- **D (sem 7+)**: 5.10, 5.22, 5.31
