# Evolução do Meu Mistério — plano de implementação

Atualizado em 07/09/2026. Este documento acompanha a evolução autorizada a partir da comparação com o ChatbotX. Itens abertos não representam funcionalidades concluídas.

## Decisão e escopo

Evoluir a base Flask/Python + React/Vite. Usar o ChatbotX como referência de experiência, organização de blocos, inbox e conectores. A Cigana continua como piloto para validar conversão e recuperação; seus comportamentos específicos devem gradualmente virar configuração e modelos reutilizáveis.

Nenhum código do ChatbotX foi incorporado neste lote. Sua [documentação](https://github.com/ChatbotXIO/ChatbotX) apresenta uma plataforma com stack diferente. A [licença](https://github.com/ChatbotXIO/ChatbotX/blob/main/LICENSE) separa a parte MIT de `apps/builder/src/enterprise`, que usa licença comercial. Antes de importar código, avaliar o arquivo, dependências e licença, e conservar os avisos aplicáveis. A lista de recursos no README não é evidência de funcionamento em produção.

## Lote implementado: ativação e primeiro atendimento

- [x] Uma única gravação de WhatsApp na tela de onboarding; preservar instruções do webhook após salvar.
- [x] Validar credenciais antes de ativar; falha de validação não deve gravar configuração nem marcar conexão ativa.
- [x] Gravar variáveis, token e vínculo do número na mesma transação; rejeitar número de outra conta sem alterar as configurações.
- [x] Criar caminho de webhook por conta, preservar em atualizações e usar o host da requisição quando `PUBLIC_URL` estiver ausente.
- [x] Distinguir conexão validada, recebimento de mensagem, fluxo publicado válido e resposta com status de envio bem-sucedido no checklist do painel.
- [x] Manter histórico incremental das versões da persona; rejeitar preços não finitos.
- [x] Não gravar seleção de template quando o template solicitado for inválido.
- [x] Oferecer modelo comercial inicial separado do blueprint de pós-pagamento da Cigana.
- [x] Modelo comercial pergunta a necessidade, espera resposta, apresenta a oferta cadastrada, coleta dúvida e encaminha para atendente. Saídas de timeout encerram a etapa sem enviar oferta fora de contexto.
- [x] Corrigir leitura de `content_text` no executor, evitando enviar somente o nome interno da etapa.
- [x] Prévia de kits reconhece `graph.nodes` e o formato antigo `nodes`; mostra mensagens e perguntas disponíveis.
- [x] Exibir erro recuperável de onboarding e aviso quando o catálogo de kits não carregar.

Referências: `api/saas/onboarding.py`, `launch_readiness.py`, `flows/business_templates.py`, `flow_executor.py`, `frontend/src/routes/Onboarding.tsx`, `frontend/src/components/LaunchChecklist.tsx` e `frontend/src/routes/Dashboard.tsx`.

O modelo comercial é um ponto de partida editável, não um vendedor autônomo completo. Copia nome e descrição da oferta no momento da criação; mudanças futuras da oferta exigem revisar o texto do blueprint. O checklist é evidência dos eventos descritos, não certificação de disponibilidade, de qualidade das respostas ou de conversão.

## 1. Fechar o ciclo completo do WhatsApp

| Etapa | Base existente | Próxima validação / critério de aceite |
|---|---|---|
| Conectar WhatsApp | Onboarding, `api/saas/integrations_whatsapp.py`, `wa_tenant_resolver.py`, `webhooks/` | Número de teste real valida credenciais, webhook e mensagens de entrada e saída sem cruzar contas. |
| Configurar negócio | Persona e oferta por conta, `api/tenant_config.py` | Perfil estruturado com público, tom, objeções, prova, oferta e limites deve alimentar o agente publicado; não basta salvar no formulário. |
| Montar e testar | Canvas React, `flow_builder_runtime.py`, `published_flow_runtime.py` | Mesma conversa no simulador e no runtime: perguntas, condições, timeout, erro de IA/API, retomada e atendimento humano. |
| Publicar | `api/flow_platform.py`, `FlowPublish` | Fluxo inválido não publica; edição de um rascunho não altera atendimento publicado sem decisão explícita; rollback demonstrado. |
| Medir | `api/saas/metrics.py`, `funnel_analytics.py` | Entrada, oferta, checkout e pagamento têm identificação e contagem consistente; duplicatas e reembolsos não viram vendas adicionais. |
| Recuperar | `ai/recovery_engine.py`, cron e configurações | Testar pagamento, opt-out, pausa humana, resposta e limite de janela antes de cada envio; medir retomada e conversão. |

- [ ] Rodar jornada em número real de teste, incluindo erro de credencial e indisponibilidade temporária.
- [ ] Confirmar isolamento com três contas em ambiente de homologação, incluindo histórico, publicação, mídia e pagamentos.
- [ ] Verificar entrega real de mensagens; um registro local sem status não prova envio.
- [ ] Validar conversão e recuperação com eventos reais, sem disparar campanhas para clientes durante testes.
- [ ] Auditar armazenamento de segredos em todos os caminhos: `TenantFlowSecret.value_cipher` e `_decrypt_secret` ainda têm caminhos em texto puro. O texto da interface não deve alegar criptografia que esses caminhos não oferecem.

## 2. Melhorar editor e atendimento

Já existem canvas, validação de grafo, execução por turno e takeover em `api/saas/inbox.py`. Reutilizar essas peças e comparar a experiência com o ChatbotX antes de substituir componentes.

- [ ] Editor: identificar o nó com erro, explicar como corrigir, permitir testar uma etapa e mostrar a transcrição do caminho percorrido.
- [ ] Publicação: distinguir rascunho de versão ativa e validar rollback sem perda de estado de conversas existentes.
- [ ] Inbox: deixar claro quem atende, por que a IA parou, como assumir e como devolver o controle.
- [ ] Handoff: validar que a pausa impede novas respostas do bot e novas recuperações até liberação; manter necessidade e dúvida acessíveis ao atendente.
- [ ] Objeções fora de ordem: responder preço, pagamento, dúvida ou pedido humano sem reiniciar o funil.
- [ ] Acessibilidade e celular: seleção de kits por teclado, foco de modal, formulários rotulados e canvas/painel utilizáveis em telas pequenas.

Aceite: operador novo configura, simula, identifica um erro e corrige, publica, assume conversa e devolve ao bot sem editar código ou consultar logs técnicos.

## 3. Separar a Cigana da plataforma

O modelo `atendimento_comercial` inaugura um caminho independente. Os fluxos espirituais e a inteligência específica em `ai/stage_intelligence.py` continuam existindo; não foram genericamente convertidos neste lote.

- [ ] Inventariar nomes, preços, checkout, ritmo, mensagens e regras de nicho em `config_cliente.py`, `personalizer.py`, `ai/` e `flows/`.
- [ ] Definir perfil de negócio versionado; manter contratos `ContextoConversa`, `Acao` e `stage_intel` compatíveis.
- [ ] Criar pacote Cigana explícito com testes de regressão e defaults que preservem o piloto.
- [ ] Criar pacote comercial com objetivos de etapa, campos obrigatórios, objeções, limites e fallback humano.
- [ ] Expor configuração simples no produto e verificar sua aplicação no motor, por conta e por versão publicada.

Aceite: Cigana e negócio comercial funcionam no mesmo motor, em contas isoladas, com textos e regras próprios e sem hardcode de um cliente vazando para outro.

## 4. Expandir canais depois da validação

Não instalar ou migrar a plataforma inteira para ChatbotX apenas pela quantidade de canais anunciados.

- [ ] Medir resultado e estabilidade do piloto WhatsApp.
- [ ] Escolher o próximo canal por demanda real dos clientes.
- [ ] Definir contrato de mensagens, contatos, mídia, status, deduplicação e capacidades por canal.
- [ ] Avaliar um conector por vez, incluindo licença e custo de adaptação do TypeScript para a arquitetura existente.
- [ ] Validar diferença de recursos e políticas de cada canal; apresentar limites na interface quando afetarem configuração.

Aceite: novo canal reutiliza conversa e funil onde compatíveis e passa testes de identidade, repetição de eventos, falhas, mídia e atendimento humano antes de liberar para clientes.

## Verificação e limites deste lote

Após o ajuste de handoff, 77 testes selecionados passaram, cobrindo onboarding, runtime publicado, integração com o motor, pausa para atendente, grafo e variáveis. O build do lote havia passado antes de alterações paralelas na tela de Sequências; a execução final ficou bloqueada por dois erros TypeScript dessa tela, fora deste lote. A validação visual local confirmou seleção do modelo e preservação da instrução de webhook após uma única gravação. Dados e credenciais usados no teste visual eram fictícios; Meta foi simulada.

- [x] Atualizar resultado final de testes após o ajuste de handoff.
- [ ] Confirmar visualmente checklist do painel com a sessão de teste.
- [ ] Homologação com Meta, IA e gateway reais permanece pendente.
- [ ] Implantação destas mudanças em produção e acompanhamento de conversão não foram comprovados por este trabalho.

Manter os itens pendentes abertos. A existência de telas, módulos ou testes unitários não deve ser registrada como prova de operação real.
