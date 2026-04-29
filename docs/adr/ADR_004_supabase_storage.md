# ADR 004 — Supabase Storage pra mídia (com plano de migração pra R2)

**Status:** Aceito
**Data:** 2026-04-28
**Decisor:** Magno Alves
**Tags:** infraestrutura, storage, mídia

## Contexto

A plataforma precisa hospedar mídia em 3 categorias:

1. **Templates compartilhados** — 78 imagens das cartas de Marselha + baralho fechado (~5MB total). Mesmas pra todos os tenants.
2. **Cache TTS por tenant** — áudios gerados pelo `tts/audio_engine.py`, com expiração (`AudioCache.expira_em` no DB).
3. **Mídia custom por tenant** — futuro: foto avatar da cigana, mídias do funil customizadas.

Inbound também tem componente de mídia: WhatsApp Cloud API gera URL temporária (5min) que precisa ser baixada e re-hospedada se vamos preservar histórico.

A `.env` do projeto já tem `NEXT_PUBLIC_SUPABASE_URL` configurado pro Postgres (Supabase).

## Decisão

**Supabase Storage no MVP.** Plano de migração pra Cloudflare R2 se egress crescer.

## Justificativa

1. **Já no stack** — Supabase já é o Postgres do projeto, zero conta nova, zero billing extra
2. **Auth integrada** — RLS policies do Postgres se estendem ao Storage
3. **CDN incluído** — entrega rápida sem configurar CloudFront
4. **Free tier generoso** — 1GB storage + 5GB egress/mês cobre ~30 tenants ativos
5. **Custo previsível** — $0.021/GB storage, $0.09/GB egress
6. **Simplicidade operacional** — uma plataforma, um dashboard, uma chave

## Plano de implementação

### Fase 2 (junto com G1-G3 do GAP doc)
- [ ] Criar bucket `templates-public` (read público, write só admin)
  - Subir 78 cartas Marselha + baralho fechado uma vez
  - URLs canônicas: `https://{project}.supabase.co/storage/v1/object/public/templates-public/marselha/{slug}.jpg`
- [ ] Criar bucket `tenant-media-{tenant_id}` (read autenticado, write só tenant owner)
  - Auto-provisionado quando tenant é criado
  - RLS policy: `auth.tenant_id() = bucket.tenant_id`
- [ ] Criar bucket `tts-cache` (read autenticado, lifecycle 30 dias)
- [ ] Criar bucket `whatsapp-inbound-media` (read interno, lifecycle 90 dias)
  - Worker baixa URL Meta dentro do prazo de 5min e persiste aqui
  - `Mensagem.media_url` aponta pra cá

### Estrutura final de buckets

```
supabase-storage/
├── templates-public/         (read público)
│   └── marselha/             (78 cartas + baralho)
├── tenant-media-{tenant_id}/ (read autenticado por tenant)
│   ├── avatar.jpg
│   └── custom/
├── tts-cache/                (read autenticado, TTL 30d)
└── whatsapp-inbound-media/   (read interno, TTL 90d)
```

## Consequências

**Positivas:**
- Setup em horas, não dias
- Sem terceiro provider pra gerenciar
- RLS unificada com Postgres

**Negativas:**
- Egress pago após free tier ($0.09/GB) — em escala alta vira gargalo de custo
- Bandwidth cap pode ser hit se 1 tenant viralizar
- Se Supabase tiver downtime, DB e Storage caem juntos

## Sinal pra migrar pra Cloudflare R2

Migrar quando **qualquer** destes ocorrer:
- Egress mensal > R$ 200
- Mais de 100 tenants ativos
- Latência de delivery virar reclamação recorrente

**R2 é melhor em escala** porque tem **egress zero** ($0/GB), o que é game-changer pra plataforma com mídia. Storage um pouco mais barato ($0.015/GB vs $0.021).

Implementação da migração será trivial se usarmos a abstração `MediaStorage` desde o dia 1 (interface comum, switch via env var).

## Alternativas consideradas

1. **AWS S3** — descartado: complexidade IAM, sem CDN nativo (precisa CloudFront extra), egress pago
2. **DigitalOcean Spaces** — descartado: maturidade menor, sem free tier relevante
3. **Backblaze B2** — descartado: integração Bunny CDN extra pra ter delivery decente
4. **Cloudflare R2 desde o dia 1** — descartado: nova conta, novo billing, complexidade extra de cold start
5. **Self-hosted MinIO** — descartado: operação que ninguém precisa

## Referências

- [Supabase Storage docs](https://supabase.com/docs/guides/storage)
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- ADR_001 (sem Chatwoot — somos donos da mídia também)
