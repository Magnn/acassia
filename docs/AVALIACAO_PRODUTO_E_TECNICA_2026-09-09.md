# Avaliação do app — produto e prontidão técnica

## Diagnóstico

O Meu Mistério já é uma plataforma ampla: builder, inbox, CRM, pagamentos, sequências, broadcast, automações sociais, analytics, área de membros, marketplace e ferramentas de desenvolvedor. A comparação com o [ChatbotX](https://github.com/ChatbotXIO/ChatbotX) mostra boa cobertura funcional. A prioridade agora deve ser consolidar o caminho que gera resultado para a Cigana Esmeralda e reduzir risco operacional, em vez de aumentar a quantidade de telas.

## P0 — antes de tráfego pago ou novos clientes

1. **Homologar a jornada dinheiro → entrega com serviços reais.** Executar Cakto e Pix aprovados, outbox, worker, WhatsApp e conteúdo entregue usando contas de produção controladas. Testes automatizados não comprovam credenciais, templates aprovados nem políticas da Meta.
2. **Aplicar as migrações no ambiente.** A cabeça atual é `d0e1f2a3b4c5`; app e worker devem iniciar somente depois do runner Alembic.
3. **Monitorar consumidores Redis.** Alertar quando `worker_alive=false`, houver DLQ, crescimento de `ready/delayed` ou entrega pós-pagamento em `failed`.
4. **Homologar o agendamento público.** A API agora lista disponibilidade, valida tenant/slot/data/hora, reserva com bloqueio e unicidade no banco e aplica rate limit. Falta validar timezone e lembretes com usuários reais.
5. **Concluir a autenticação B2C no frontend.** A API agora emite token assinado e protege cofre/agenda; o cliente deve armazenar e enviar `Authorization: Bearer`, tratar expiração e oferecer logout/recuperação.

## P1 — para operação SaaS confiável

1. **Transformar `app.py` em application factory.** Importar o módulo ainda instancia IA, inicia monitores e tenta conexões externas. Isso dificulta testes, migrações, CLI e múltiplos workers.
2. **Separar domínios.** Há aproximadamente 700 regras Flask. Pagamentos, flows, leads, health e integrações devem sair gradualmente do arquivo principal para blueprints com contratos únicos.
3. **Testar contratos externos.** Criar testes sandbox/contract para Meta, Mercado Pago, Stripe e o checkout escolhido, incluindo timeout, 429, 5xx, redelivery e respostas parcialmente válidas.
4. **Completar operação dos outboxes.** Painel com filtro, idade do job, tentativas, reprocessamento e alerta. Definir SLO para pagamento aprovado até primeira entrega.
5. **Reforçar compliance.** Consentimento por canal, origem do opt-in, retenção de payloads, exportação/exclusão de dados e bloqueio central antes de qualquer envio proativo.

## P2 — crescimento do produto

1. Medir o funil piloto: conversa iniciada, avanço por fase, checkout, aprovação, entrega, resposta e recuperação.
2. Criar templates de negócio reutilizáveis a partir do funil vencedor, mantendo copy, preço e delays em configuração.
3. Completar canais na ordem de demanda comprovada. Instagram Messaging e e-mail tendem a agregar mais ao funil atual que reproduzir todos os conectores do ChatbotX.
4. Implementar adaptador fiscal e checkout Cakto somente contra documentação e sandbox oficiais.
5. Publicar SDK/CLI/MCP com versionamento, documentação de scopes e exemplos; hoje os clientes existem no repositório, mas ainda não são pacotes distribuídos.
6. Trocar os `stub` do simulador por efeitos simulados tipados para IA, API, integração, A/B e motor Python, sem realizar chamadas externas na prévia.

## Correções feitas durante esta avaliação

- Removidos quatro contratos de rota duplicados que dependiam da ordem de registro do Flask.
- Criado teste que impede regressão de rotas duplicadas.
- Cofre e agenda B2C agora exigem token assinado e bloqueiam acesso cruzado por `consumer_id`.
- Signup e login B2C receberam limites de requisição; senha mínima passou a oito caracteres.
- Agendamento público passou a validar tenant e usar `Lead.telefone`, `Lead.nome` e `Lead.node_atual` corretamente.
- Falha no processamento Stripe libera a claim idempotente e responde `500`, permitindo redelivery.
- Agendamento público passou a reservar slots atomicamente e o banco impede duas reservas no mesmo horário por tenant.
- Telemetria de produto agora fica restrita ao tenant autenticado, mesmo quando a URL tenta solicitar outro tenant.
- A vitrine deixou de atribuir uma especialidade inventada e esconde experts suspensos, removidos ou inativos.

## Critério de lançamento

Liberar o piloto quando a jornada real de pagamento e entrega passar repetidamente, as filas estiverem observáveis, o agendamento reservar slots de forma atômica e não existirem rotas de dados pessoais baseadas apenas em IDs fornecidos pelo cliente. A expansão omnichannel deve vir depois dos dados de conversão e retenção do piloto.
