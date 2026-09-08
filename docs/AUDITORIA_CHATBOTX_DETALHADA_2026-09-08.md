# Auditoria detalhada contra ChatbotX

Referência analisada: ChatbotX `b6ed384bee8fdc36a788e79be484eba903f3e773` em 08/09/2026. A comparação usou o código real de workers, scheduler, integrações, imports, SDK e banco, além do projeto local em `968c478`.

## Conclusão

O Meu Mistério já tem mais produto vertical do que o ChatbotX em espiritualidade, conteúdo e monetização, mas ainda não possui a mesma fundação de mensageria. O erro recorrente é declarar paridade quando existe uma rota ou tela, mesmo que o fluxo operacional, a recuperação de falhas e o contrato multicanal não estejam completos.

## Achados críticos

### 1. O lease da fila expira durante broadcasts normais e pode duplicar mensagens

- Local: `api/utils/task_queue.py:16,86-95,153-158` usa lease fixo de 300 segundos e não o renova.
- Local: `api/saas/broadcast.py` espera entre 1 e 30 segundos por destinatário. Uma campanha com 151 contatos e delay de 2 segundos já passa de cinco minutos.
- Quando o lease expira, outro worker recoloca o mesmo job na fila enquanto o primeiro continua trabalhando. Como ambos podem ter carregado destinatários `pending`, existe envio duplicado.
- ChatbotX usa BullMQ, locks por dispatch, concorrência limitada e jobs identificados; no scheduler, o lock é por dispatch e o envio recebe `jobId` estável.

Correção: renovar o lease enquanto o job executa, tornar cada destinatário um job idempotente e guardar o ID retornado pelo provedor. Broadcast não deve ser um único job longo.

### 2. O broadcast transforma falha interna em sucesso

- Local: `api/saas/broadcast.py:811-820` captura a exceção externa, marca a campanha como `completed` e não relança.
- A fila recebe retorno normal e executa ACK. Portanto retry e DLQ nunca entram em ação nesse tipo de falha.

Correção: marcar `failed` ou `paused`, persistir o erro e relançar para a fila. Conclusão deve depender da situação terminal de todos os destinatários.

### 3. A idempotência social pode perder mensagens definitivamente

- Local: `api/public/social_automations.py:144` grava o recibo antes das chamadas externas em `:166` e `:169`.
- As funções externas retornam `False`, mas o resultado não altera o recibo nem gera retry.
- Se a Meta responder com erro temporário, a reentrega do webhook será descartada como duplicada e a DM nunca será enviada.
- Story Reply repete o mesmo padrão entre `:272` e `:285`.

Correção: persistir um evento com estados `pending/processing/sent/failed`, responder 200 ao webhook, processar na fila e marcar cada efeito separadamente. Deduplicação precisa impedir repetição depois do sucesso sem impedir retry depois de falha.

### 4. “Sync WhatsApp” não sincroniza WhatsApp

- Local: `api/saas/contacts_import.py:245-266` conta leads que já existem, cria um registro `completed` e devolve esse número como `synced_contacts`.
- Não consulta o provedor, não importa contatos, conversas, mensagens, mídia ou cursor de continuação.

Correção: remover a alegação de sincronização até existir um conector real; implementar job paginado por dispositivo, cursor persistido, upsert de identidade externa e progresso retomável.

### 5. As novas tabelas não têm migração Alembic

- Local: `SocialWebhookReceipt` e `GrowthLink` foram adicionadas em `db/models.py:2164-2190`.
- Não existe revisão em `alembic/versions` para essas tabelas nem para `public_api_keys.scopes`.
- `db/sync.py:125` cobre somente a coluna de scopes e `create_all` é usado como migração implícita. Isso não oferece downgrade, auditoria de rollout nem controle consistente em múltiplas instâncias.

Correção: criar uma revisão Alembic explícita, testar upgrade a partir do schema de produção e retirar alterações de schema ad hoc do boot.

### 6. A migração de Growth Links quebra links antigos até o dono abrir a tela

- Local: a migração legada roda apenas em `api/saas/growth_links.py:78`, na listagem autenticada.
- O redirect público em `:148` procura somente a tabela nova.
- Depois do deploy, um QR antigo retorna 404 até o tenant visitar a página de Growth Tools.

Correção: backfill de dados na migração/deploy antes de trocar a leitura; manter dual-read temporário durante a transição.

## Achados altos

### 7. Sequências ainda não têm um dispatch persistido equivalente ao ChatbotX

O local usa `ContactOnSequence.next_run_at` como claim temporário e só cria `SequenceDispatch` depois da tentativa. Uma queda depois da aceitação pelo WhatsApp e antes do commit pode reenviar. O ChatbotX cria primeiro um dispatch com `idempotencyKey`, estado, tentativa, horário e enrollment; depois usa lock e job ID derivados do dispatch.

Correção: adicionar `enrollment_id`, `run_at`, `attempt`, `provider_message_id` e chave idempotente única ao dispatch. O scheduler deve operar sobre dispatches, não diretamente sobre enrollments.

### 8. O endpoint manual ignora a fila

- Local: `api/saas/sequences.py:718-720` chama `process_due_sequence_steps` dentro do request.
- Pode bloquear a requisição e cria um segundo caminho operacional diferente do worker.

Correção: o endpoint deve somente enfileirar e devolver `202` com job ID.

### 9. A importação inteira acontece no request e sem limite de bytes

- Local: `api/saas/contacts_import.py:93` recebe todas as linhas em JSON e `:126` processa uma a uma.
- Não há upload streaming, limite por bytes, chunks, checkpoint ou retomada.
- O ChatbotX possui parsers CSV/XLSX, validação de arquivo e `stream-guard` com limite acumulado de bytes.

Correção: upload para storage, validação streaming, job de import, lotes transacionais e cursor persistido.

### 10. O adapter é usado em poucos caminhos e não representa capacidades

- `ChannelType` anuncia seis canais, porém o registry implementa WhatsApp, Telegram e Webchat.
- Broadcast, conteúdo, eventos, agenda, tarot, espiritual e aura chamam o cliente WhatsApp diretamente.
- O modelo local suporta basicamente texto/mídia/botões genéricos. O upstream converte explicitamente template WhatsApp, lista, flow, carrossel e IDs de mensagens do provedor.

Correção: declarar capabilities por adapter; centralizar envio, normalização de erros, IDs do provedor e status. Migrar cada caminho direto antes de anunciar omnichannel.

### 11. API scopes permitem acesso total às chaves antigas silenciosamente

- Local: `api/v1/auth.py:27` só bloqueia quando `scopes` é não vazio.
- Uma chave antiga com `[]` recebe todos os poderes, embora uma lista vazia normalmente signifique nenhum poder.

Correção: migrar chaves antigas para scopes explícitos ou marcar `legacy_full_access` com expiração; depois tratar `[]` como nenhum acesso.

### 12. Falta o plano operacional do worker novo

Existe `task_worker.py`, mas não há definição de processo no deploy nem health/readiness próprio. Com `TASK_WORKERS_IN_WEB=0`, o web aceita jobs no Redis mesmo se nenhum consumer estiver ativo.

Correção: declarar o processo worker na plataforma, criar health com heartbeat, métricas de lag/DLQ e alerta de fila sem consumidor.

## Diferenças estruturais que não são bugs isolados

O ChatbotX separa builder, realtime, worker, CLI e MCP; possui pacotes de event bus, imports, scheduler, SDK e adapters independentes. O Meu Mistério concentra grande parte disso no Flask e em módulos SaaS. Não é necessário copiar o monorepo ou trocar de linguagem, mas precisamos reproduzir as fronteiras operacionais:

1. evento persistido;
2. job pequeno e idempotente;
3. worker observável;
4. adapter com capabilities e erros normalizados;
5. mensagem com ID do provedor e lifecycle;
6. API/SDK construídos sobre o mesmo serviço de aplicação usado pela UI.

## Ordem de correção

1. Corrigir broadcast: erro deve falhar o job; quebrar por destinatário; heartbeat de lease; idempotência e provider message ID.
2. Refazer eventos sociais como outbox/worker com estados e retry.
3. Criar migração Alembic e backfill de Growth Links antes do próximo deploy.
4. Transformar sequência em dispatch persistido e retirar processamento inline.
5. Substituir o falso sync WhatsApp e a importação em request por jobs paginados.
6. Migrar envios diretos para adapters e adicionar capabilities/status.
7. Corrigir scopes legados e adicionar idempotency key/paginação/OpenAPI à API.
8. Configurar e monitorar o processo worker em produção.

## Referências do ChatbotX usadas

- `packages/sequence-scheduler/src/dispatch-manager.ts`
- `apps/worker/src/sequence-scheduler/worker-consumer.ts`
- `packages/worker-config/src/lib/connection.ts`
- `packages/imports/src/stream-guard.ts`
- `integrations/whatsapp/src/handlers/message/outgoing-message/index.ts`
- `apps/worker/src/integration/routing.ts`
