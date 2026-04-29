# Checklist — publicar fluxo (antes de campanha)

Copie para o Notion ou use como impressão. Alinha com o **Flow Builder**: Rascunho → Validar → Servidor → Publicar.

---

## Antes de abrir o builder

- [ ] **Oferta e links** — checkout/pagamento e prova social batem com o que o fluxo promete.
- [ ] **WhatsApp (Meta)** — número ativo, webhook acessível, token não expirado (Integrações no painel).
- [ ] **Tenant** — se usa multi-tenant, confirme o tenant certo (canto / configurações).

---

## No Flow Builder (ordem sugerida)

1. [ ] **Montar ou ajustar** o canvas (blocos e ligações).
2. [ ] **Rascunho** — grava neste browser (evita perder trabalho ao fechar o separador).
3. [ ] **Validar** — deve passar sem erro crítico; se falhar, leia a mensagem ou abra a aba **Logs**.
4. [ ] **Servidor** — grava o blueprint na base (SQLite/servidor do projeto).
5. [ ] **Publicar** — torna esta versão a publicada para o tenant (motor usa esta).
6. [ ] *(Opcional)* **Compilar** / **Simular** / **Sim. canvas** — teste sem WhatsApp real.

---

## Teste manual rápido (2–3 minutos)

- [ ] Número de teste recebe a **primeira mensagem** esperada após o gatilho.
- [ ] Resposta típica do lead (ex.: “sim”, nome, “quero”) **avança** o que deveria.
- [ ] **Duplicata**: reenviar a mesma mensagem **não** deve duplicar efeito (onde aplicável).

---

## Go / no-go

- [ ] **Go** — checklist acima OK; pode ligar tráfego ou lista.
- [ ] **No-go** — falha em Validar ou teste manual; **não** escalar anúncio até corrigir.

---

## Se algo quebrar (sem ser programador)

Anote em **uma frase**: o que fez, o que esperava, o que aconteceu (+ print). Quem codifica ou a IA no repo resolve com isso.

## Ver também

- **`docs/checklist-staging-flow-builder-execute.md`** — validação em staging com **Executar lead** (condição, divisão, API, GPT, `motor_ref`, flags `.env`).
- **Funil estático Meu Mistério (mapa no canvas)** — modelo JSON em **`assets/flow_templates/meumisterio_estatico.json`**. No painel, **Importar fluxo** e escolher esse ficheiro (mesmo fluxo que **Novo fluxo** + rascunho local). Copy e delays de produção continuam em `flows/funil_estatico_meu_misterio/roteiro.py` até migrar tudo para o executor.

*Última revisão alinhada ao dashboard AcassIA (Flow Builder).*
