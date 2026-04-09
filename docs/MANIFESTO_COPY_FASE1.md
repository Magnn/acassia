# Manifesto de Copy — Fase 1

## Objetivo

Garantir que toda evolução de copy na fase 1 preserve:

- fluidez de conversa no WhatsApp frio;
- percepção de leitura real (presença + direção);
- estabilidade do funil (sem travar, sem repetir, sem pular contrato).

Este documento é a fonte de verdade editorial para `node1`, `node2`, `node3` e `node4`.

---

## Leis Imutáveis (não negociáveis)

### Lei do Node 1 (Abertura)

Sequência obrigatória:

1. saudação;
2. apresentação;
3. vaga/consulta inicial gratuita;
4. fechamento:
   - sem nome: pedir nome;
   - com nome: convite para iniciar.

Restrições:

- não remover nenhum bloco estrutural;
- não trocar ordem dos blocos;
- não transformar abertura em mensagem única seca.

### Lei do Node 2 (Contato)

Padrão atual:

- se contato já confirmado: não dispara texto, segue para `node3`;
- se não confirmado: envia `vcard` com contexto afirmativo, sem perguntar confirmação, e segue para `node3`.

Restrições:

- proibido voltar para "conseguiu salvar?" no fluxo padrão;
- proibido pausar em `node2` esperando confirmação explícita.

### Lei do Node 3 (Coleta Profunda)

Ordem de camadas:

1. foto + desabafo;
2. desejo;
3. aprofundamento (tempo/tentativas);
4. extração e handoff.

Restrições:

- não repetir pedido de foto se `foto_recebida` já está verdadeiro;
- não repetir pergunta idêntica na mesma camada;
- não avançar ignorando campos centrais sem fallback definido.

### Lei do Node 4 (Instagram)

Padrão atual:

- se insta já confirmado: bypass silencioso para `node5`;
- se não confirmado: envio afirmativo de perfil/link (sem pergunta) e avanço para `node5`.

Restrições:

- não reinserir pergunta de confirmação no fluxo padrão;
- não parar no `node4` aguardando resposta para continuar.

---

## Princípios de Linguagem (tom)

- **Humano, direto, respeitoso**: acolhe sem parecer script corporativo.
- **Espiritual com pé no chão**: místico sem teatralizar demais.
- **Curto e completo**: frase curta com sentido fechado.
- **Sem ruído técnico**: jamais exibir linguagem interna de sistema.
- **Sem agressividade comercial**: convite e direção, sem pressão.

---

## Regras de Segurança de Copy

- Nunca terminar balão em frase quebrada.
- Evitar duplicação semântica entre balões consecutivos.
- No máximo uma pergunta principal por turno (quando aplicável).
- Links em balão isolado quando necessário.
- Evitar travessão longo e construções com risco de corte.

---

## Variações Permitidas por Perfil

As variações abaixo são permitidas **sem violar as leis dos nodes**:

- **Lead racional/cético**: menos metáfora, mais clareza prática.
- **Lead emocional/ferido**: mais acolhimento, mesma direção objetiva.
- **Lead objetivo/curto**: menos preâmbulo, manter estrutura.
- **Lead com dor explícita**: espelhar dor com frase breve, sem drama excessivo.
- **Lead de preço**: responder com transparência de consulta inicial sem virar pitch.

O que nunca muda: contrato estrutural do node.

---

## Checklist de Mudança de Copy (obrigatório)

Antes de aprovar qualquer alteração em fase 1:

1. Quebrou alguma lei imutável do node?
2. A mudança removeu bloco obrigatório?
3. Introduziu pergunta de confirmação onde hoje é fluxo afirmativo?
4. Aumentou risco de repetição/pergunta duplicada?
5. Preservou avanço de estado (`prox`) sem depender de novo input do lead?
6. Passou na suíte de regressão da fase 1?

Se qualquer resposta for "sim" para risco estrutural, a mudança não entra.

---

## Política de Evolução

- Melhoria de copy deve ser incremental e testável.
- Toda mudança de tom deve manter comportamento de estado.
- Toda mudança de estado deve manter coerência de tom.
- Se houver conflito entre "criatividade" e "estabilidade", vence estabilidade.

---

## Definição de Qualidade Final (Fase 1)

Uma copy de fase 1 é considerada pronta quando:

- conversa flui sem pausas artificiais;
- lead entende o próximo passo sem confusão;
- o texto soa humano e consistente com a persona;
- não há repetição irritante;
- o funil não depende de correção manual para avançar.

