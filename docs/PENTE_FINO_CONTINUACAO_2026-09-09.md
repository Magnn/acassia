# Continuação do pente-fino após o Codex

Base revisada: commit `8cc6a31`, que incorporou o trabalho pendente após o Antigravity.

Referência usada para comparação: [ChatbotX](https://github.com/ChatbotXIO/ChatbotX), incluindo os diretórios [apps](https://github.com/ChatbotXIO/ChatbotX/tree/main/apps) e [packages](https://github.com/ChatbotXIO/ChatbotX/tree/main/packages).

## Confirmado no código

- Pós-pagamento possui outbox persistente, fila Redis, retry/DLQ e endpoint de reenvio.
- O webhook Cakto valida assinatura, reivindica eventos de forma idempotente e agenda a entrega pelo blueprint.
- Emissão fiscal e checkout Cakto não retornam mais sucessos inventados.
- Runs manuais entram na fila e registram início, conclusão ou falha.
- Providers WhatsApp expõem resultado estruturado e as capabilities não prometem recursos ignorados.
- Sequências usam chave estável por matrícula e passo.
- O worker publica heartbeat e a aplicação não executa DDL no boot de PostgreSQL.
- Growth Links possuem tabela e script de backfill.

## Correções desta continuação

- Eventos sociais agora persistem o payload original. O webhook apenas valida, grava e enfileira; se a fila estiver indisponível responde `503`. Retry administrativo reutiliza o payload real.
- Broadcast faz claim condicional por destinatário. Claims abandonados são recuperados após 15 minutos e cada envio conserva chave idempotente e ID do provider.
- Importações foram movidas para o worker. A API responde `202`, o payload fica persistido, o progresso é salvo em lotes de 100 e o histórico é atualizado pela interface.

## Ainda depende de produto ou fornecedor

- Adaptador fiscal oficial e credenciais do emissor escolhido.
- Endpoint oficial da Cakto para criação de checkout.
- Coex, sincronização retroativa do WhatsApp e webhook completo do Pix.
- Messenger, Instagram Messaging, e-mail e TikTok como canais completos.
- Expansão da API pública v1 e distribuição versionada dos clientes conforme prioridade comercial.
- Nós ainda exibidos como `stub` no simulador precisam de semântica de simulação definida para cada integração externa.

Esses itens não devem simular sucesso. Até serem implementados, permanecem explicitamente indisponíveis ou falham de forma controlada.

## Ferramentas para desenvolvedores

- SDK Python: `sdk/client.py`.
- CLI: `python scripts/meu_misterio_cli.py --help`.
- MCP stdio: `MM_BASE_URL=... MM_API_KEY=... python mcp_server.py`.

As três ferramentas usam a API pública v1 e, portanto, herdam autenticação por escopo, isolamento por tenant e os mesmos erros HTTP.
