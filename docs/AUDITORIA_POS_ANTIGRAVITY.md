# Reauditoria pós-Antigravity

Atualizada em 08/09/2026 sobre o código até `011f332`, comparado ao ChatbotX `main`. Esta revisão substitui os estados transitórios de `AUDITORIA_PARIDADE_CHATBOTX.md`; presença de arquivo ou nome “parity” não foi considerada prova de produção.

## O que foi realmente entregue

| Área | Estado atual | Evidência |
|---|---|---|
| Sequências | **Implementada, não homologada em produção** | CRUD, passos, agenda, inscrição manual/por tag/API, envio WhatsApp real, claim atômico, retry, métricas, UI e testes. |
| Importação CSV | **Implementada para lotes em memória** | Mapeamento, upsert, tags, histórico, erros e inscrição em sequência. Carga inteira ainda chega como JSON ao servidor. |
| Inbox/takeover | **Ampliado** | Importação pela UI, controle humano e atualização em tempo real. Ainda falta teste real de concorrência/reconexão. |
| Split traffic | **Implementado** | Nó A/B e configuração visual, apoiados pelas tabelas de exposição existentes. |
| Growth links/QR | **Implementado básico** | Tabela indexada por ID opaco, QR e incremento atômico. Ainda não atribui clique a contato/conversão. |
| Cofre | **Corrigido** | Fernet versionado, compatibilidade de leitura legada e consumidores WhatsApp atualizados. |
| Webchat | **Protegido** | Chave de site, sessão assinada, allowlist de origem, widget atualizado e rate limit. |
| Comment-to-DM | **Implementado básico** | Match por palavra, resposta pública, private reply, captura de lead e recibo idempotente persistido. |
| Story Replies | **Implementado após correção** | Configuração e envio para recipient ID; a primeira versão chamava a função com argumentos incompatíveis. |
| ChannelAdapter | **Contrato inicial** | WhatsApp, Telegram e webchat possuem adapters e API v1 usa o registry. O runtime principal ainda não foi migrado integralmente. |
| Developer API v1 | **MVP endurecido** | Credenciais só em headers, scopes por chave, ping, envio, contatos e inscrição em sequência. |
| Fila Redis | **Durável** | Reserva com lease, ACK, retry exponencial, DLQ, recuperação e processo worker separado. |

## O que ainda falta — prioridade real

### P0 — segurança e integridade

Os três itens P0 desta rodada foram resolvidos: API keys somente em headers com scopes, recibos idempotentes para comentários/Stories e Growth Links normalizados em tabela indexada.

Resolvidos após esta reauditoria: credenciais novas de `WADevice` ficam no cofre por dispositivo e são apagadas ao desativá-lo; o setup do Telegram exige login, grava token/segredo cifrados e o webhook valida `X-Telegram-Bot-Api-Secret-Token`. As colunas antigas permanecem apenas para leitura compatível até uma migração de dados zerá-las.

### P1 — confiabilidade

1. **Importação não suporta carga grande.** O navegador parseia/envia todas as linhas em JSON e o request processa uma a uma. Usar upload de arquivo, job assíncrono, chunks, progresso e retomada.
2. **Chamadas sociais ainda executam dentro do webhook.** Já são idempotentes, porém resposta pública e DM bloqueiam o request da Meta e ainda precisam entrar na fila com retry.
3. **Exactly-once externo depende do provedor.** O claim das sequências impede concorrência e o histórico evita reenvio após confirmação; uma queda entre a aceitação pelo WhatsApp e o commit pode gerar retry. Propagar chave idempotente quando o provedor oferecer suporte.

### P1 — contratos e API

1. **Adapter não é omnichannel completo.** Só três adapters estão registrados. Instagram, Facebook e Email aparecem no enum, mas não são implementados; TikTok, Zalo e Email continuam ausentes.
2. **Registry tinha fallback perigoso.** Canal desconhecido virava WhatsApp. Foi corrigido para retornar `422`, evitando enviar pelo canal errado.
3. **Capacidades não são declaradas.** Falta `ChannelCapabilities` para template, botão, mídia, localização, catálogo, carrossel, reação, janela e status.
4. **Runtime principal ainda usa caminhos diretos.** Diversos módulos continuam chamando `horoscope._get_whatsapp_client`; criar adapter não conclui a migração.
5. **API v1 ainda não tem idempotency key, paginação, webhooks de saída ou erros padronizados.** Scopes e autenticação somente por header já foram concluídos; ainda há dois decoradores independentes a consolidar.
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

1. Mover efeitos sociais e importações grandes para a fila durável.
2. Completar API v1 com idempotência, paginação, webhooks e OpenAPI gerado.
3. Conectar clique de Growth Link a lead e conversão.
4. Migrar os caminhos de envio para `ChannelAdapter` e declarar capacidades.
5. Homologar WhatsApp, Telegram, webchat e Meta Social com credenciais reais em contas isoladas.
6. Ampliar canais, SDK/CLI/MCP e white-label conforme demanda comercial.

## Verificação desta rodada

- Build de produção do frontend: passou.
- Regressão de cofre, onboarding, API v1, adapters, social, webchat, sequências e importação: passou nos conjuntos executados.
- Testes específicos após as correções de canal e Story Reply: 23 passaram.
- Integrações externas foram testadas com mocks; isso não comprova permissões, políticas, entrega nem status reais nas plataformas.
