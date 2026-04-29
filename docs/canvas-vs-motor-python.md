# O que o canvas faz hoje vs o motor Python

Documento para **copy, operações e decisão de produto** — evita confundir o **Flow Builder** (tela de nós) com o **motor de conversa** que atende cada mensagem no WhatsApp.

---

## Duas “faixas” no mesmo produto

| | **Flow Builder (canvas)** | **Motor Python (`flows/fase_*`, `engine`)** |
|---|---------------------------|-----------------------------------------------|
| **Onde vive** | Dashboard → Fluxos → desenho em grafo; JSON guardado como **blueprint** | Código Python por fase/nó (`node_1_apresentacao`, funil estático, etc.) |
| **Melhor analogia** | Roteiro de **campanha / sequência** que você **compila** e pode **disparar** | **Cérebro da conversa** que decide o que responder a **cada mensagem** do lead |
| **Quando corre** | Quando **validas**, **publicas** e sobretudo quando **executas** no lead ou chamas a API de execute | **Sempre** que chega mensagem (e em recuperações, pós-venda, etc.) |

**Em uma frase:** o canvas prepara **pacotes de ações** (texto, mídia, delay) e **publicação de versão**; o motor Python **mantém o estado** (`node_atual`, metadata do lead) e **roteia** a conversa dia a dia.

---

## O que o canvas **já faz bem**

- Desenhar blocos, ligar nós, guardar **rascunho** e **blueprint no servidor**.
- **Validar** e **compilar** o documento (estrutura, ciclos, ordem linear de passos).
- **Publicar** uma versão do blueprint para o **tenant** (metadados de “qual documento está oficial”).
- **Executar no lead** (botão / API): transforma o fluxo compilado em **ações** e envia pela **mesma fila WhatsApp** que o resto do sistema — ideal para **jornadas disparadas** (pós-opt-in, teste, sequência pontual).

---

## O que o canvas **ainda não substitui** (expectativa tipo Manychat)

- **Cada mensagem inbound a seguir só o grafo desenhado** — hoje o caminho principal de quem **escreve no Zap** continua a ser o **motor por `node_atual`** e ficheiros em `flows/`, não o blueprint linha a linha.
- **Ramos condicionais reais** (se A vai para B, senão C) na execução automática — a compilação é **linear**; ramos avançados estão no **roadmap** técnico.
- **Tags, audiências e broadcast** ao estilo ferramenta pura de marketing — não são o foco atual do canvas.

Ou seja: podes **vender e operar** com sequências e com o **funil que já existe em código**; o canvas acelera **desenho + validação + disparos**, mas **não** é ainda o único dono de toda a conversa.

---

## Como as duas faixas **conectam** (sem misturar papéis)

1. **Inbound** (lead manda mensagem) → `engine` → nó Python atual → novas `Acao`.
2. **Blueprint execute** (tu ou API disparam o fluxo) → `flow_executor` → mesma fila de envio → WhatsApp.

O **publicar** blueprint **não**, por si, faz com que **todas** as mensagens seguintes ignorem o motor antigo — isso seria um projeto à parte (ver `docs/roadmap-canvas-orbita.md`, fase D).

---

## Para copy e campanhas — o que comunicar

- **“O nosso funil no ar”** = sobretudo o **motor** + config (`config_cliente`, links, oferta) + o que está **testado** em telefone real.
- **“O fluxo no canvas”** = **versão desenhada** do que queres enviar; **validar + publicar + testar execute** antes de escalar tráfego (usa também `docs/checklist-publicacao-fluxo.md`).

Se alguém perguntar *“isto já é Manychat?”*: **não** — tens **controlo próprio** e **IA integrada** no projeto; o canvas **caminha** para mais paridade, mas **a verdade operacional** hoje é **motor + blueprint onde já estiver ligado**.

---

## Ver também

- `docs/roadmap-canvas-orbita.md` — backlog técnico por fases.
- `docs/checklist-publicacao-fluxo.md` — checklist antes de campanha.
