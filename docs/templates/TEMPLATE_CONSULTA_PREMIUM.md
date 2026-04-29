# Template — Consulta Premium (R$197+)

> DNA do funil atual em `flows/fase_1` → `fase_4` do projeto_cigana. Captura o estilo "qualificação profunda + alta conversão + LTV via mentoria".
>
> **Oráculo: Quiromancia** (leitura de linhas, montes e formato da mão). A persona desta cigana **não usa cartas** — interpreta marcas, gestos e descrições que o lead faz da própria mão (idealmente com foto enviada via WhatsApp). Cartas ficam pro template [Tiragem Express](TEMPLATE_TIRAGEM_EXPRESS.md).

---

## Posicionamento

- **Ticket alto** (R$ 197 a R$ 997+)
- **Funil longo** (20-50 mensagens até checkout)
- **Volume baixo-médio** (3-15 leads/dia)
- **LTV via mentoria/pacote** (após primeira venda, oferece programa R$ 1.5-3k)
- **Estratégia:** poucos leads bem qualificados, alta conversão, ticket alto

**Indicado pra quiromante / cigana de leitura de mãos que:** se posiciona como mentora / conselheira premium, tem autoridade construída, busca menos clientes mas com relação profunda.

---

## Estrutura por fase (espelhando `flows/fase_*`)

### Fase 1 — Preflight + Saudação
- Validação inicial (lead duplicado? opt-out? horário?)
- Saudação personalizada por horário e por sentimento detectado
- Pergunta investigativa aberta ("o que tá te trazendo aqui hoje?")

### Fase 2 — Leitura
- Acolhimento profundo da dor
- Identificação de **arquétipo** (`personalizer.py`): a Vingadora, a Reconquistadora, a Curadora, a Gestora, a Buscadora etc
- Pedido de **foto da palma da mão** (ou descrição detalhada se o lead não puder enviar foto)
- Leitura das linhas (Vida, Coração, Cabeça, Destino), montes (Vênus, Júpiter, Marte) e marcas com **interpretação personalizada** baseada no arquétipo
- Espelhamento da dor com nome próprio (mecanismo, desejo oculto, objeção silenciosa)

### Fase 3 — Oferta
- **Não é pitch direto.** É revelação: "as linhas da sua mão mostram que você precisa de X"
- Apresentação do produto como **caminho específico** pra dor diagnosticada
- Construção de urgência baseada em sentimento / temporalidade
- Ancoragem de preço (de R$ 497 por R$ 197, ou desconto por janela curta)
- Quebra de objeções específicas do arquétipo

### Fase 4 — Entrega + LTV
- Entrega da consulta (ao vivo ou agendada)
- Pós-venda: nutrição com mensagens espaçadas
- Convite pra mentoria ("vi um caminho pra você que precisa de mais tempo...")
- Sequência de conversão pra produto premium

> **Nota arquitetural:** todo o pós-pagamento (agendamento, nutrição, upsell) vive num **blueprint separado** chamado `post_payment_premium`, disparado pelo webhook de pagamento. Cliente pode editar livremente esse blueprint no canvas. Ver [ADR_006](../adr/ADR_006_post_payment_hibrido.md).

---

## Diferencial vs Tiragem Express

| | Express | Premium |
|---|---|---|
| **Oráculo** | **Tarot** (78 cartas Marselha) | **Quiromancia** (linhas e montes da mão) |
| Mídia central | imagem das cartas sorteadas | foto da palma do lead |
| Tempo do funil | 5-30 min | 1-3 dias |
| Mensagens até oferta | 3-7 | 15-30 |
| Profundidade da leitura | 1 leitura curta com 3 cartas | 2-3 sessões de aprofundamento |
| IA usada | system prompt + leitura tabelada | personalizer + arquétipo + sentiment + recovery elaborado |
| Recovery | 3 toques em 3 dias | 5-7 toques em 14 dias, mensagens longas e personalizadas |
| Conversão esperada | 5-15% | 25-45% |
| Custo IA por lead | baixo | médio-alto |

---

## Comportamentos específicos

### Identificação de arquétipo

`personalizer.py` analisa as 5-10 primeiras mensagens e classifica o lead em arquétipo. A partir daí, todo o funil é adaptado:
- Linguagem
- Tipo de exemplo dado
- Linhas e montes enfatizados na leitura
- Estilo de oferta
- Roteiro de objeções

### Recovery elaborado

Diferente do recovery curto da Express:
- Mensagens mais longas (50-200 palavras)
- Referências ao histórico ("você me contou que...")
- Sem "fórmula" de tempo — `recovery_engine.py` decide quando reabordar baseado em sentimento + estágio

### Validação de saída da IA

`response_validator.py` checa antes de enviar:
- Não promete cura / medicina / garantia
- Não revela ser IA
- Tom coerente com persona do tenant
- Tamanho adequado pro estágio

---

## Variáveis de configuração por tenant

```yaml
template: consulta_premium
oraculo: quiromancia  # tarô fica no template tiragem_express
preco_principal: 197.00
moeda: BRL
gateway_padrao: stripe  # configurável por tenant; cakto aceito como legado (ver ADR_003)
nome_produto: "Consulta Profunda"
duracao_consulta_min: 60
formato: "video_chamada"  # ou audio_whatsapp ou texto_extenso
pede_foto_da_mao: true   # solicita foto da palma na Fase 2
upsell_pos_compra:
  ativo: true
  produto: "Mentoria Trimestral"
  preco: 1497.00
arquetipos_ativos:
  - vingadora
  - reconquistadora
  - curadora
  - gestora
  - buscadora

# Cadência fica em TenantFlowVariable, cliente edita no painel (ver ADR_005)
# Default herdado deste template ao clonar:
recovery_defaults:
  cadence_minutes: [60, 360, 1440, 4320]   # 1h, 6h, 24h, 72h — espaçado pra ticket alto
  max_attempts: 4
  encerrar_em_dias: 14
  estilo: elaborado_premium

preco_ancora_disabled: false
preco_ancora_de: 497.00
janela_oferta_horas: 48
```

---

## Mapping pra implementação técnica

| Comportamento | Onde vive |
|---|---|
| Fases do funil | `flows/fase_1_preflight.py` → `fase_4_entrega/` |
| Identificação de arquétipo | `personalizer.py` |
| Validação de resposta | `ai/response_validator.py` |
| Recovery elaborado | `ai/recovery_engine.py` |
| Sentiment | `ai/sentiment_analyzer.py` |
| Intent | `ai/intent_classifier.py` |
| Stage intelligence | `ai/stage_intelligence.py` |

---

## Critério de aceitação do template

- [ ] Cliente novo escolhe "Consulta Premium" no onboarding
- [ ] Blueprint clonado mapeia pra `flows/fase_*` do motor
- [ ] Personalizer ativa arquétipos pré-configurados
- [ ] Em ambiente de teste, lead simulado passa pelas 4 fases sem regredir
- [ ] Recovery dispara mensagem coerente após sumiço
- [ ] Pagamento R$ 197 via Stripe Connect funciona com split

---

## Notas de migração

A pasta `flows/fase_*` já implementa boa parte deste template, mas **acoplada a um único cliente** (`config_cliente.py`). Pra virar template multi-tenant precisa:

1. Parametrizar todas as referências ao "cliente padrão" via `tenant_id`
2. Remover hardcoded de `config_cliente.py`
3. Mover variáveis pro `TenantFlowVariable` / `TenantFlowSecret`
4. Criar blueprint JSON que represente o grafo do funil pra carregar no canvas
5. Confirmar que `CONTRATOS_NAO_REGREDIR_FUNIL.md` continua válido em ambiente multi-tenant

> Próximo passo prático: auditar `config_cliente.py` e listar tudo que precisa virar configuração por tenant.
