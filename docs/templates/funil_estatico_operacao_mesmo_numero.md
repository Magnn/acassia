# Operacao no mesmo numero (agente + estatico)

Guia rapido para rodar funil estatico no mesmo WhatsApp da agente avancada sem conflito.

## 1) Chave de roteamento (obrigatorio)

Defina uma regra unica para o fluxo estatico:

- `keyword_gate`: `quero minha consulta`
- `flow_kind`: `static`
- `priority`: maior que outros fluxos genericos de entrada

Se a mensagem inicial nao bater com o gate, o runtime pode seguir para o fluxo da agente avancada.

## 2) Agente avancada inativa (durante teste)

No periodo de testes:

- desative auto-disparo da agente avancada no numero
- mantenha apenas o gatilho do fluxo estatico ativo
- monitore eventos por `lead_id` para garantir um unico executor por conversa

## 3) Troca IA -> estatico por fase (futuro)

Pode conectar sim. Recomendado:

- Fase 1 (IA): usar bloco `agente_ia` para coleta/qualificacao
- Condicao de saida IA: salvar `meta.next_phase = "fase2_estatico"`
- Fase 2 (estatico): `goto` para no inicial do roteiro de audios/imagens

Contrato minimo para a troca:

- preservar `lead_id`, historico e metadata
- marcar `owner_mode` por etapa (`ia` ou `static`)
- evitar dois executores simultaneos no mesmo `lead_id`

## 4) Asset da imagem de Instagram

No template salvo:

- arquivo de fluxo: `docs/templates/funil_estatico_meu_misterio_bloco1.acassia-flow.json`
- campo da imagem: `content_media_url = assets/instagram/meumisterio_perfil.jpg`

Copie a imagem para esse caminho no ambiente de deploy, ou ajuste para URL publica/CDN.

## 5) Bloco 2 — audio PTT (gravado na hora)

- Arquivo no repositorio: `assets/funil_estatico_meu_misterio/audio/bloco2_ptt.ogg`
- Origem local copiada de: `WhatsApp Ptt 2026-03-04 at 14.23.16 (1).ogg` (Downloads)
- No JSON do fluxo: `whatsapp_delivery: ptt_as_recorded_now` (executor deve enviar como PTT nativo, nao encaminhado)
- Sequencia: texto energias → delay **240s** (4 min) → audio → delay **12s** → pergunta nome → aguarda texto → delay **35s** → fim bloco 2 (`goto_bloco_3`)
