# Reauditoria pós-Antigravity

Atualizada em 08/09/2026 sobre o código até `0f2c9a8`, comparado ao ChatbotX `main`. Esta revisão substitui os estados transitórios de `AUDITORIA_PARIDADE_CHATBOTX.md`; presença de arquivo ou nome “parity” não foi considerada prova de produção.

## O que foi realmente entregue

| Área | Estado atual | Evidência |
|---|---|---|
| Sequências | **Implementada, não homologada em produção** | CRUD, passos, agenda, inscrição manual/por tag/API, métricas, UI e testes. |
| Importação CSV | **Implementada para lotes em memória** | Mapeamento, upsert, tags, histórico, erros e inscrição em sequência. Carga inteira ainda chega como JSON ao servidor. |
| Inbox/takeover | **Ampliado** | Importação pela UI, controle humano e atualização em tempo real. Ainda falta teste real de concorrência/reconexão. |
| Split traffic | **Implementado** | Nó A/B e configuração visual, apoiados pelas tabelas de exposição existentes. |
| Growth links/QR | **Implementado básico** | Link rastreado, QR e contador de clique. Ainda não atribui clique a contato/conversão. |
| Cofre | **Corrigido** | Fernet versionado, compatibilidade de leitura legada e consumidores WhatsApp atualizados. |
| Webchat | **Protegido** | Chave de site, sessão assinada, allowlist de origem, widget atualizado e rate limit. |
| Comment-to-DM | **Implementado básico** | Match por palavra, resposta pública, private reply, captura de lead e testes mockados. |
| Story Replies | **Implementado após correção** | Configuração e envio para recipient ID; a primeira versão chamava a função com argumentos incompatíveis. |
| ChannelAdapter | **Contrato inicial** | WhatsApp, Telegram e webchat possuem adapters e API v1 usa o registry. O runtime principal ainda não foi migrado integralmente. |
| Developer API v1 | **MVP** | Ping, envio, upsert/leitura/tags de contato e inscrição em sequência. |
| Fila Redis | **Protótipo operacional** | Producers e consumers para broadcast/sequence. Não atende ainda às garantias de uma fila durável. |

## O que ainda falta — prioridade real

### P0 — segurança e integridade

1. **Credenciais de `WADevice` continuam em texto puro.** `evolution_api_key` e `meta_access_token` são gravados diretamente na tabela e usados diretamente pelo provider. Migrar para o cofre por `device_id`, limpar colunas legadas e nunca serializar esses campos.
2. **Telegram ainda tem endpoint de setup público.** `/api/webhooks/telegram/setup` recebe o token no body, usa `GET` com token na URL da API Telegram e não exige login. Deve virar configuração autenticada, guardar token no cofre e validar o header secreto do webhook.
3. **API keys são aceitas na query string.** Isso vaza em logs, histórico e proxies. Aceitar apenas `Authorization: Bearer` ou `X-API-Key` e acrescentar scopes por chave.
4. **Comment-to-DM não é idempotente.** Reentrega do webhook pode responder e mandar DM novamente. Persistir `comment_id/event_id`, registrar tentativa/resultado e deduplicar antes de efeitos externos.
5. **Growth redirect varre todas as contas.** O redirect consulta todos os registros `growth.links`; além de não escalar, amplia o impacto de colisões/enumeração. Criar tabela indexada com ID opaco único e tenant associado.

### P1 — confiabilidade

1. **A fila Redis não é durável como anunciado.** `BLPOP` remove a tarefa antes do sucesso; não há ACK, lease, retry exponencial, contador de tentativas, DLQ nem recuperação de worker morto. Os consumers são threads daemon dentro do processo Flask.
2. **Fallback perde garantia.** Sem Redis, broadcast volta para thread local e sequência executa inline. Em produção deve falhar fechado ou persistir job no banco, nunca prometer agendamento durável.
3. **Sequência não possui claim atômico robusto por dispatch.** Duas instâncias podem buscar o mesmo vencimento. Criar chave idempotente `(enrollment, step)` e claim transacional antes do envio.
4. **Importação não suporta carga grande.** O navegador parseia/envia todas as linhas em JSON e o request processa uma a uma. Usar upload de arquivo, job assíncrono, chunks, progresso e retomada.
5. **Growth counters sofrem lost update.** Links são uma lista JSON lida/modificada/regravada; cliques concorrentes podem se perder.
6. **Chamadas sociais executam dentro do webhook.** Resposta pública e DM bloqueiam o request da Meta e não têm retry. Validar, persistir evento, responder `200` e executar em worker.

### P1 — contratos e API

1. **Adapter não é omnichannel completo.** Só três adapters estão registrados. Instagram, Facebook e Email aparecem no enum, mas não são implementados; TikTok, Zalo e Email continuam ausentes.
2. **Registry tinha fallback perigoso.** Canal desconhecido virava WhatsApp. Foi corrigido para retornar `422`, evitando enviar pelo canal errado.
3. **Capacidades não são declaradas.** Falta `ChannelCapabilities` para template, botão, mídia, localização, catálogo, carrossel, reação, janela e status.
4. **Runtime principal ainda usa caminhos diretos.** Diversos módulos continuam chamando `horoscope._get_whatsapp_client`; criar adapter não conclui a migração.
5. **API v1 não tem scopes, idempotency key, paginação, webhooks de saída ou erros padronizados.** Também há dois decoradores independentes de API key (`api/v1/auth.py` e `api/public/v1/astrology.py`).
6. **OpenAPI continua manual e incompleto.** Deve ser gerado a partir das rotas/schemas da API v1 e validado em CI.

### P2 — paridade de produto

1. SDK TypeScript/Python, CLI e servidor MCP.
2. Inbox realmente multicanal com identidade externa por canal e união segura de contatos.
3. Facebook Messenger, Instagram Messaging, TikTok Messaging, Email e Zalo completos.
4. Facebook Lead Ads com deduplicação, consentimento, atribuição e início de fluxo/sequence.
5. Integrações pedidas pelo mercado: Google Sheets, ActiveCampaign, Mailchimp/Klaviyo/SendGrid. Hoje existem cofre e runner parcial, não produtos completos.
6. Catálogo/produtos e mensagens ricas portáveis entre canais.
7. Filtros/segmentos relacionais salvos, pastas e campos de sistema consistentes.
8. White-label completo, domínio customizado e reseller.
9. Internacionalização da UI e das mensagens do sistema.

## Recursos que ainda são apenas estrutura

- **TikTok:** valida segredo e recebe evento, mas não transforma mensagens/leads nem responde.
- **YouTube:** salva configuração; não publica, consome eventos nem cria broadcast.
- **Telegram:** adapter textual existe, mas onboarding, webhook seguro, mídia, status e operação real não estão fechados.
- **ActiveCampaign/Google Sheets:** aparecem no cofre/runner/editor; faltam autenticação, gestão, UX, webhooks, erros e testes ponta a ponta.
- **Email/Facebook/Instagram no enum:** enumeração não significa adapter disponível.

## Próxima sequência recomendada

1. Migrar segredos de `WADevice` e proteger Telegram.
2. Trocar a fila atual por processamento com ACK/retry/DLQ e worker separado.
3. Adicionar idempotência aos efeitos sociais e às sequências.
4. Normalizar Growth Links em tabela e conectar clique → lead → conversão.
5. Endurecer API v1: scopes, somente headers, idempotência, paginação e OpenAPI gerado.
6. Migrar os caminhos de envio para `ChannelAdapter` e declarar capacidades.
7. Homologar WhatsApp, Telegram, webchat e Meta Social com credenciais reais em contas isoladas.
8. Só então ampliar canais, SDK/CLI/MCP e white-label.

## Verificação desta rodada

- Build de produção do frontend: passou.
- Regressão de cofre, onboarding, API v1, adapters, social, webchat, sequências e importação: passou nos conjuntos executados.
- Testes específicos após as correções de canal e Story Reply: 23 passaram.
- Integrações externas foram testadas com mocks; isso não comprova permissões, políticas, entrega nem status reais nas plataformas.
