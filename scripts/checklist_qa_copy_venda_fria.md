# Checklist QA - Copy e Interacao (Venda Fria Direta)

Use este checklist para validar o funil em teste real no WhatsApp.
Marque cada item com `PASS` ou `FAIL`.

## Regras de execucao

- Rodar 3 cenarios completos (A, B, C) do `node_1` ate `node_8`.
- Nao pular mensagens do lead; responder de forma natural.
- Registrar print ou log curto de cada bloco que falhar.
- Se 1 item critico falhar, o teste do cenario ja fica reprovado.
- Sempre validar `80% conhecido + 20% novo`: comecar no que o lead ja acredita e so depois instalar a nova crenca.

## Cenarios obrigatorios

### Cenario A - Amor de volta (tom arrogante como defesa)
- Entrada exemplo: `Quero trazer ela de volta. Vai comer na palma da minha mao.`
- Objetivo: validar personalizacao profunda e quebra de casca emocional.

### Cenario B - Amor de volta (lead morno e cético)
- Entrada exemplo: `Nao sei se isso funciona, mas quero tentar entender.`
- Objetivo: validar cadeia logica e construcao de crenca sem promessa magica.

### Cenario C - Separacao / novo ciclo
- Entrada exemplo: `Quero separar e seguir minha vida em paz.`
- Objetivo: validar adaptacao de mecanismo e linguagem de desejo correto.

---

## Checklist por bloco

## 1) Coleta (nodes 2-5)

- [ ] **Nome limpo**: capturou nome sem erro e usou vocativo humano.
- [ ] **Desejo declarado**: bot identificou o que a pessoa quer (objetivo final).
- [ ] **Sem redundancia**: nao repetiu a mesma pergunta de desejo sem necessidade.
- [ ] **Perguntas com pausa**: toda pergunta terminou o turno aguardando resposta.
- [ ] **Tentativas previas** (critico): houve pergunta clara sobre o que o lead ja tentou.
- [ ] **Sem presuncao**: nao afirmou "voce ja tentou de tudo" sem evidencia.
- [ ] **Universo correto** (critico): classificou corretamente (amor_de_volta, separar, novo amor, etc.).
- [ ] **Dados concretos capturados** (critico): tempo, pessoa, fato ou frase forte do lead foi salvo para eco futuro.

## 2) Leitura (node 6)

- [ ] **Ancoragem no texto real** (critico): pelo menos 1 bloco ecoa frase/atitude real do lead.
- [ ] **Sem generico de internet** (critico): leitura nao parece template reutilizado.
- [ ] **Cadeia logica minima** (critico): existe sequencia P1->P2->P3->P4->P5 (crenca inevitavel).
- [ ] **Expansao de dor**: mostra impacto pratico, emocional e de decisao.
- [ ] **Expansao tripla** (critico): funcional + dimensional + emocional no ponto central de dor.
- [ ] **Story brand negativo**: aparece externo + interno + filosofico (injustica percebida).
- [ ] **Xeque-mate claro**: fecha com pergunta de confirmacao forte.
- [ ] **Pausa apos pergunta** (critico): bot espera o lead responder antes de avancar.
- [ ] **Nome do lead distribuido**: usa o nome ao longo da leitura sem soar robotico.

## 3) Agitacao e desejo (node 7)

- [ ] **Reacao ao ultimo input** (critico): primeiro bloco responde ao "sim/nao" do lead.
- [ ] **Sem recitar script**: nao ignora a resposta e nao reinicia narrativa do zero.
- [ ] **Desejo em foco**: vende o que a pessoa quer, sem sermao de "o que precisa".
- [ ] **Tom simples e humano**: linguagem curta, conversa de WhatsApp, sem texto literario.
- [ ] **Transferencia de culpa com empatia**: remove culpa sem atacar o lead.
- [ ] **Tentativas desqualificadas com respeito** (critico): valida o que lead tentou e explica por que nao tocou a raiz.
- [ ] **Mecanismo com nome especifico** (critico): nao usa "trabalho espiritual" generico.
- [ ] **Urgencia real** (critico): sem timer falso; janela espiritual contextualizada ao agora.
- [ ] **CTA de continuidade**: pergunta objetiva para seguir ao proximo passo.

## 4) Oferta (node 8)

- [ ] **Transicao emocional correta** (critico): preco aparece apos pico emocional, nao frio.
- [ ] **Oferta ancorada no desejo** (critico): valor ligado ao resultado que o lead pediu.
- [ ] **Sem prometer milagre**: sem garantia absoluta ou prazo magico.
- [ ] **Mini-transacoes completas** (critico): confianca -> mecanismo -> compromisso -> preco -> prova -> urgencia -> objecao -> CTA.
- [ ] **Logica de ticket**: bucket inicial 130/100/65 distribuido corretamente.
- [ ] **Negociacao correta** (critico): respeita escada 130->100->50 e 65->40->30.
- [ ] **FIRMO antes do link**: link so sai apos confirmacao.
- [ ] **Preco com ancoragem**: mostra custo de nao resolver, nao so numero.

## 5) Conversa e experiencia

- [ ] **Interacao real** (critico): pergunta sempre abre espaco de resposta do lead.
- [ ] **Sem atropelo de nodes** (critico): nao emenda bloco apos pergunta sem pausa.
- [ ] **Baloes curtos**: mensagens legiveis em celular (sem parede de texto).
- [ ] **Sem repeticao feia**: nao repete frase-identidade no mesmo trecho.
- [ ] **Sem erros proibidos** (critico): sem mecanismo generico, sem urgencia falsa, sem ignorar resposta do lead.

## 6) Adaptacao por ceticismo

- [ ] **Ceticismo baixo**: tom mais caloroso sem perder clareza.
- [ ] **Ceticismo medio**: equilibrio entre observacao concreta e espiritual.
- [ ] **Ceticismo alto** (critico): mais prova logica, menos floreio, com dados concretos nos blocos 4 e 5.

---

## Criterio de aprovacao

- **Aprovado por cenario**: 100% dos criticos em PASS + minimo 80% total PASS.
- **Aprovado da versao**: 3/3 cenarios aprovados.
- **Se reprovar**: corrigir e retestar apenas os cenarios com FAIL critico.

## Matriz de pontuacao (0-100)

Use esta regra para comparar versoes de copy com numero, sem achismo.

- Item **critico**: `PASS = 4 pontos` | `FAIL = 0`
- Item **nao critico**: `PASS = 2 pontos` | `FAIL = 0`
- Score final do cenario = `(pontos obtidos / pontos maximos) * 100`

### Pesos por secao

- Coleta (nodes 2-5): 20 pontos
- Leitura (node 6): 25 pontos
- Agitacao (node 7): 20 pontos
- Oferta (node 8): 20 pontos
- Conversa e experiencia: 10 pontos
- Adaptacao por ceticismo: 5 pontos
- **Total**: 100 pontos

### Faixas de decisao

- `90-100`: pronto para escalar trafego
- `80-89`: bom, ajustar apenas refinamentos
- `70-79`: converte em lead quente, fraco para morno
- `<70`: reprovado para venda fria

### Gate de seguranca (obrigatorio)

Mesmo com score alto, a versao reprova se qualquer um destes falhar:

- Perguntas sem pausa real
- Node 7 nao reage ao ultimo input do lead
- Mecanismo generico (sem nome especifico)
- Urgencia falsa
- Negociacao fora da escada definida

## Log de resultado (copiar e preencher)

```
Data:
Cenario: A | B | C
Resultado geral: APROVADO | REPROVADO
Criticos com FAIL:
- 
Nao criticos com FAIL:
- 
Trecho que mais soou generico:
- 
Trecho que melhor converteu:
- 
Acao corretiva:
- 
```

## Quadro de comparacao (antes vs depois)

```
Versao avaliada:
Data:

CENARIO A (amor de volta - defesa arrogante)
- Score antes:
- Score depois:
- Delta:
- Criticos que sairam de FAIL -> PASS:

CENARIO B (amor de volta - morno/cetico)
- Score antes:
- Score depois:
- Delta:
- Criticos que sairam de FAIL -> PASS:

CENARIO C (separacao/novo ciclo)
- Score antes:
- Score depois:
- Delta:
- Criticos que sairam de FAIL -> PASS:

MEDIA GERAL
- Antes:
- Depois:
- Delta:

Decisao final:
- Escalar | Ajustar e retestar | Reprovar
```

## Automacao rapida de score

Arquivos de apoio:

- `scripts/qa_copy_score_template.json` (preencher PASS/FAIL por item)
- `scripts/calcular_score_qa_copy.py` (calcula score por cenario e decisao)

Comando:

`py scripts/calcular_score_qa_copy.py scripts/qa_copy_score_template.json`

Saida esperada:

- score por cenario A/B/C
- lista de criticos com FAIL
- falhas de gate de seguranca
- decisao automatica para cada cenario

