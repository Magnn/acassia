# Pente-fino pós-Antigravity

Estado revisado: `814a0d8`, incluindo os commits do Antigravity `56faa60` e `e49b7dc`.

## O que foi corrigido de verdade

- A fila renova leases, possui retry, DLQ, métricas e worker separado.
- O broadcast relança falhas externas e não conclui com destinatários pendentes.
- Growth Links têm tabela própria, contador atômico e leitura compatível dos links antigos.
- Sequências possuem dispatch, claim, tentativa, chave idempotente e ID de mensagem.
- API keys vazias não ganham scopes implicitamente.
- Docker Compose possui app, worker, Redis, PostgreSQL e runner de migração.
- Capabilities básicas foram adicionadas aos três adapters registrados.

## Bloqueadores de produção

### 1. Pagamento aprovado não executa a entrega

`api/payments/dispatch.py` compila o blueprint pós-pagamento, mas `_enfileirar_acoes_pendente` apenas escreve `PENDING ENQUEUE` no log. O webhook pode ser considerado tratado e idempotente sem que produto, mensagem ou fluxo seja entregue ao comprador.

Necessário: persistir um job/outbox de entrega, executar as ações no motor, acompanhar estado e permitir retry manual seguro.

### 2. Fiscal cria nota autorizada fictícia

`api/saas/fiscal.py:24-51` gera ID, número, chave de acesso e URLs aleatórios e marca a nota como autorizada. Isso não pode ficar acessível em produção porque gera evidência fiscal falsa.

Necessário: bloquear emissão sem provider configurado; distinguir homologação; integrar provider real e validar webhook/status antes de marcar autorizada.

### 3. Checkout Cakto devolve URL fabricada

`api/saas/integration_runners.py:127-138` exige token, mas não chama a Cakto. Retorna uma URL construída localmente como se o checkout tivesse sido criado.

Necessário: implementar a API real ou retornar `not_supported`; nunca devolver sucesso simulado.

### 4. Execução manual do fluxo não executa o fluxo

`api/flow_platform.py:752-783` cria `FlowRun` com `source=manual_run_stub` e um evento inicial, porém não agenda nem executa nós.

Necessário: enviar o run ao mesmo executor usado pelos gatilhos ou expor claramente apenas uma operação de criação de rascunho.

### 5. Eventos sociais continuam presos ao request do webhook

Comment-to-DM e Story Reply fazem chamadas HTTP à Meta antes de responder ao webhook. O estado por efeito agora evita repetir uma resposta pública quando só a DM falhou, mas não existe retry interno. Se a Meta aceitar o webhook e não o reenviar, receipts `failed` ficam parados.

Necessário: webhook valida e persiste; worker executa cada efeito; scheduler recupera `failed`; endpoint administrativo lista e reprocessa DLQ.

### 6. Broadcast ainda é um job monolítico

O heartbeat reduz duplicação por expiração do lease, mas uma campanha inteira continua dentro de um job. Pausa do processo, falha persistente do Redis ou perda do heartbeat pode permitir concorrência. Destinatários são carregados como `pending` sem claim individual.

Necessário: job por lote pequeno ou destinatário, claim transacional por recipient e chave idempotente persistida junto ao provider message ID.

### 7. O provider WhatsApp ainda retorna booleano

`WhatsAppProvider.enviar_mensagem` promete `bool`. O adapter recupera o WAMID por variável thread-local específica do Meta Cloud. Evolution e outros providers não entregam um `SendResult` consistente; tracking e deduplicação ficam incompletos.

Necessário: mudar o contrato para `SendResult` em todos os providers e persistir `message_id`, erro normalizado e resposta bruta segura.

## Integridade e operações

### 8. Capabilities anunciam recursos que `send_message` ignora

O adapter WhatsApp declara botões, templates e reações, mas o método usa apenas texto ou mídia. `OutboundMessage.buttons` e metadados de template não são convertidos em payload do canal.

Necessário: capabilities derivadas do provider/dispositivo e handlers reais por tipo. Rejeitar explicitamente formatos não suportados.

### 9. Dispatch de sequência ainda pode duplicar na janela provider → commit

A chave inclui `attempt`. Cada retry cria uma chave nova. Se o WhatsApp aceitar a mensagem e o processo cair antes de marcar `sent`, a tentativa seguinte possui outra chave e pode reenviar.

Necessário: uma chave estável por ocorrência agendada `(tenant, enrollment, step, run_at)` e retries sobre o mesmo dispatch.

### 10. Importação continua síncrona e em memória

O endpoint recebe `rows` completos em JSON e processa tudo na requisição. Não há limite de bytes, storage, chunks, checkpoint ou retomada. O falso sync WhatsApp foi bloqueado com `501`, mas a sincronização real ainda não existe.

Necessário: upload streaming, arquivo em storage, job assíncrono, lotes transacionais, progresso e cursor.

### 11. Health da fila não prova que existe consumer

`/api/health/queues` mostra Redis e profundidade, mas não heartbeat do worker. O web pode aceitar jobs enquanto nenhum worker está vivo.

Necessário: heartbeat periódico por processo, idade do último heartbeat, lag do job mais antigo e readiness/alerta.

### 12. Schema ainda é alterado durante boot

Apesar das migrações novas, `app.py` chama `sync_database()` e `db/sync.py` executa `create_all` e `ALTER TABLE`. Múltiplas instâncias podem disputar DDL e divergências deixam de ser detectadas pelo Alembic.

Necessário: Alembic como única fonte de evolução de schema em produção; `sync_database` limitado a desenvolvimento/testes.

### 13. Migração legada de Growth Links ainda varre tenants

O dual-read impede 404, mas o redirect de um link antigo consulta todos os blobs `growth.links`. É aceitável apenas durante uma janela curta de migração.

Necessário: backfill offline, métrica de registros restantes e remoção do dual-read após conclusão.

## Segurança multi-tenant a revisar

Há buscas secundárias somente por ID em módulos como pipeline, trilhas, agenda, avaliações, grupos e leituras. Algumas são seguras porque o objeto pai já foi filtrado pelo tenant; outras dependem dessa suposição e não possuem teste cruzado.

Necessário: testes sistemáticos com dois tenants para cada rota mutável e helpers internos recebendo `tenant_id`, além de RLS efetivo no PostgreSQL.

## Funcionalidades declaradas, mas incompletas

- Coex é stub.
- Facebook Messenger, Instagram Messaging e Email aparecem no enum, mas não têm adapter registrado.
- TikTok recebe estrutura de webhook, sem produto completo de mensagens/leads.
- Sync retroativo WhatsApp retorna `501`.
- Pix ainda documenta webhook como TODO no provider.
- Pós-pagamento não entrega o blueprint.
- Fiscal não possui provider real.
- SDK, CLI e MCP equivalentes ao ChatbotX não existem.
- Webhooks de saída, paginação e idempotency key da API v1 ainda faltam.
- Importação Google Sheets/ActiveCampaign existe parcialmente, com UX, OAuth, retry e observabilidade incompletos.
- Simulador do builder representa vários tipos de nós como stubs.

## Ordem recomendada

1. Desativar sucessos simulados: fiscal, Cakto, manual run e pós-pagamento.
2. Ligar pós-pagamento ao motor por outbox durável.
3. Mover efeitos sociais para worker com retry por efeito.
4. Quebrar broadcast por recipient/lote e estabilizar a chave do dispatch de sequência.
5. Unificar `SendResult` dos providers e implementar capabilities reais.
6. Implementar importação assíncrona e sync real por provider.
7. Remover DDL do boot e concluir backfills.
8. Criar matriz automatizada de isolamento multi-tenant.
9. Completar API, canais e ferramentas de desenvolvedor conforme prioridade comercial.

## Verificação desta rodada

- Suíte anterior após as últimas correções: 503 testes e 22 subtestes passaram.
- Build frontend passou.
- Docker Compose validou.
- Alembic apresentou uma única cabeça.
- Esses resultados validam regressões conhecidas; não homologam integrações externas nem eliminam os bloqueadores acima.
