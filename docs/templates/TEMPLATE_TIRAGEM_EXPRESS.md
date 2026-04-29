# Template — Tiragem Express (R$19-49)

> DNA extraído da pasta `cigana_tarot/` (referência histórica). Não modificar `cigana_tarot/`. Este documento descreve o template como ele será materializado no `FlowBlueprint` do projeto_cigana.
>
> **Oráculo: Tarot** (78 cartas de Marselha — implementado em [`flows/tarot/cartas.py`](../../flows/tarot/cartas.py)). Quiromancia fica pro template [Consulta Premium](TEMPLATE_CONSULTA_PREMIUM.md).

---

## Posicionamento

- **Ticket inicial baixo** (R$ 19,90)
- **Funil curto** (3-10 mensagens até checkout)
- **Volume alto** (10-50 leads/dia possível)
- **Recorrência** via "Tiragem Mensal", "Tiragem do Amor", "Tiragem da Lua Cheia" etc
- **Estratégia:** pague baixo agora, encanta com qualidade, recorre

**Indicado pra tarólogo que:** quer movimentar muitos leads, tem tempo limitado pra atender manualmente, busca recorrência > LTV grande de poucas vendas.

---

## Estrutura do prompt em 3 camadas

Inspiração: `cigana_tarot/1_prompts/zara_personalidade.md`.

### Camada 1 — System Prompt (a alma)

Imutável durante a conversa. Define:
- Identidade (nome, tom, dom)
- Restrições absolutas (não promete cura, não dá conselho médico/jurídico)
- Estilo de fala (português coloquial, frases curtas, reticências, sem emoji excessivo)
- Modo de leitura (cartas reais, conexão dor-carta, especificidade)

### Camada 2 — Injeção de contexto dinâmico

Variáveis que o engine injeta antes de cada chamada Gemini:
- `{{HORA_ATUAL}}` — pra ajustar tom (manhã / tarde / noite / madrugada)
- `{{NOME_LEAD}}` — se conhecido
- `{{NODE_ATUAL}}` — fase do funil
- `{{ULTIMO_SENTIMENTO}}` — humor detectado
- `{{ARQUETIPO}}` — perfil identificado pelo `personalizer`
- `{{HISTORICO_RESUMIDO}}` — últimos N turnos compactados pelo `context_compressor`

### Camada 3 — Prompts de situação

Cada nó do funil tem seu próprio prompt complementar:
- Saudação inicial
- Acolhimento da dor
- "Envia o baralho fechado e pede 3 números"
- "Sorteia e revela 3 cartas"
- Leitura aprofundada
- Oferta R$19,90
- Recovery (3 níveis crescentes)

---

## Funil mecânico (12 etapas)

```
Trigger: lead manda primeira mensagem
    ↓
[1. Saudação acolhedora]
    ↓
[2. Pergunta investigativa] (qual a dor? amor / dinheiro / família / espiritual?)
    ↓
[3. Espelhamento] (devolve a dor com palavras de poder)
    ↓
[4. Envia baralho fechado] (foto pra criar ritual)
    ↓
[5. Pede 3 números 1-9] (cria engajamento, ancora a "magia")
    ↓
[6. Aguarda números]
    ↓
[7. Sorteia 3 cartas] (envia 3 imagens)
    ↓
[8. Leitura específica] (conecta cada carta à dor revelada)
    ↓
[9. Pausa dramática + oferta]
    ↓
[10. Link Stripe / Cakto R$19,90]
    ↓
[Webhook pagamento aprovado]
    ↓
[11. Entrega da tiragem completa]
    ↓
[12. Convite recorrência] ("posso te avisar quando o céu estiver bom pra você?")
```

**Recovery branches** (se lead some em qualquer ponto):
- T+5min: mensagem mística curta ("senti algo no ar...")
- T+1h: pergunta direta ("conseguiu sentir as cartas?")
- T+1d: oferta com escassez ("hoje a Lua tá cheia, energia diferente")
- T+3d: encerramento elegante (sai do recovery; opt-out automático)

> **Nota arquitetural:** as etapas 11-12 (entrega + recorrência) vivem num **blueprint separado** chamado `post_payment_express`, disparado pelo webhook de pagamento. Cliente pode editar livremente esse blueprint no canvas. Ver [ADR_006](../adr/ADR_006_post_payment_hibrido.md).

---

## Comportamentos específicos

### Quebra de mensagens em balões

Resposta longa do agente é dividida em 2-4 balões com:
- Pausa entre balões: 1-3s (proporcional ao tamanho)
- "Status digitando" simulado entre balões
- Ordem natural (não revela tudo de uma vez)

Implementação: `engine.py` já faz parte disso; consolidar com referência ao sub-workflow `07_zara_quebrar_mensagens.json`.

### Consciência de horário (booster de conversão)

| Faixa | Tom | Frase-âncora |
|---|---|---|
| 06-11h | Esperançoso | "A manhã traz clareza..." |
| 12-17h | Direto | "Vou direto ao que as cartas mostram..." |
| 18-22h | Reflexivo | "No fim do dia a gente olha pro que importa..." |
| 23-05h | Íntimo, urgente (**maior conversão**) | "Sei que você não tá dormindo..." |

### Sorteio de cartas

- Cartas reais do Tarot de Marselha (78 cartas)
- 3 imagens enviadas em sequência (com pausa)
- Não inventar carta — usar tabela canônica
- Storage: imagens hospedadas em Supabase Storage (uma vez, reutilizadas por todos os tenants)

---

## Variáveis de configuração por tenant

```yaml
template: tiragem_express
preco_principal: 19.90
moeda: BRL
gateway_padrao: stripe  # configurável por tenant; cakto aceito como legado (ver ADR_003)
nome_produto: "Tiragem de Emergência"
upsell_pos_compra:
  ativo: true
  produto: "Tiragem Mensal Recorrente"
  preco: 49.90

# Cadência fica em TenantFlowVariable, cliente edita no painel (ver ADR_005)
# Default herdado deste template ao clonar:
recovery_defaults:
  cadence_minutes: [5, 60, 180]    # Protocolo Magno agressivo
  max_attempts: 3
  encerrar_em_dias: 3
  estilo: magno_agressivo

horario_boost:
  ativo: true
  faixa_madrugada: "23:00-05:00"

# Mídia em Supabase Storage (ver ADR_004)
imagens_baralho:
  fechado_url: "https://{project}.supabase.co/storage/v1/object/public/templates-public/marselha/baralho_fechado.jpg"
  cartas_dir: "https://{project}.supabase.co/storage/v1/object/public/templates-public/marselha/"
```

---

## Mapping pra implementação técnica

| Comportamento do template | Onde vive no projeto_cigana |
|---|---|
| System prompt persona | `StudioAgent` + `StudioAgentVersion.body_json` |
| Funil 12 etapas | `FlowBlueprint.body_json` (template semente) |
| Recovery scheduler | `flow_executor` + `FlowSchedule` (cron) |
| Quebra de balões | `engine._processar_fila_corpo` |
| Consciência de horário | `personalizer.py` |
| Sorteio cartas | nó `motor_ref` no canvas → função Python (a criar) |

---

## Critério de aceitação do template

- [ ] Cliente novo escolhe "Tiragem Express" no onboarding
- [ ] Blueprint clonado, persona base populada
- [ ] Cliente customiza nome da cigana, preço, oferta
- [ ] Em até 5 minutos depois do onboarding, manda mensagem de teste e recebe saudação acolhedora coerente
- [ ] Funil completo até pagamento aprovado funciona em ambiente de teste
- [ ] Recovery dispara nas 3 janelas configuradas

---

## Comportamentos do `cigana_tarot/` que ainda precisam ser portados pro engine

Lista de gap a ser confirmada lendo `engine.py`:

- [ ] Sub-workflow `02_zara_enviar_baralho` — envio de foto fechada
- [ ] Sub-workflow `03_zara_sorteio_cartas` — sorteio + 3 imagens
- [ ] Sub-workflow `07_zara_quebrar_mensagens` — quebra de balões
- [ ] `09_zara_recuperacao_leads` — cron 5min de recovery
- [ ] Whisper (transcrição de áudio) — opcional mas recomendado pra capturar voz do lead

> Próximo passo prático: comparar engine.py linha-a-linha com esses comportamentos e listar exatamente o que falta.
