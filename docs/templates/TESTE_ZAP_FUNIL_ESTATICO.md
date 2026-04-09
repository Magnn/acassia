# Teste no WhatsApp real (fluxo estático até o Bloco 2)

## Atalho automatizado (recomendado)

Com o projeto na pasta atual e dependências instaladas:

```bash
python scripts/e2e_static_flow_whatsapp.py
```

Opcional: número real do seu WhatsApp (DDI+DDD+número, sem `+`):

```bash
python scripts/e2e_static_flow_whatsapp.py 5511999887766
```

O script sobe o `app.py` se nada estiver escutando, cria o lead se precisar, importa o blueprint e chama `execute`. Para mensagens chegarem de verdade, use o **seu** número e `PUBLIC_URL` com **HTTPS** (túnel) para imagem/áudio.

---

O endpoint `POST /api/flows/blueprints/<id>/execute` **enfileira todas as ações** geradas pelo JSON (textos, delays, imagem, áudio). Os nós `wait_until` **não pausam** o motor hoje: eles são omitidos na conversão para `Acao`, então o fluxo **não espera** foto ou nome do lead entre blocos — serve para validar **ordem, textos, mídia e delays** no Zap.

Para um funil que **pare** e espere resposta, o runner precisará integrar esses nós com o estado da conversa (futuro).

## Pré-requisitos

1. **App rodando** (`python app.py` ou o processo que vocês usam em produção).
2. **Mesmo `ACASSIA_TENANT_ID`** no processo do motor e no header da API (se usar multi-tenant).
3. **`PUBLIC_URL` com HTTPS** acessível pela Meta (túnel ngrok, Cloudflare Tunnel, domínio).  
   Ex.: `PUBLIC_URL=https://abc123.ngrok-free.app`  
   Sem isso, **imagem e áudio por link** falham: a API exige URL pública; caminhos `assets/...` viram `PUBLIC_URL/assets/...` automaticamente no `engine`.
4. **Imagem do Instagram** em `assets/instagram/meumisterio_perfil.jpg` (ou altere o JSON para uma URL `https://` pública).
5. **Áudio** já está em `assets/funil_estatico_meu_misterio/audio/bloco2_ptt.ogg`.

## 1) Importar o blueprint

O corpo deve ter `title`, `slug` e `body` = documento `acassia-flow` completo (o mesmo do arquivo `funil_estatico_meu_misterio_bloco1.acassia-flow.json`, com `format`, `version`, `graph`, etc.).

Exemplo com `curl` (ajuste host e tenant):

```bash
curl -s -X POST "http://127.0.0.1:5000/api/flows/blueprints/import" ^
  -H "Content-Type: application/json" ^
  -H "X-Acassia-Tenant: default" ^
  -d @- <<'EOF'
{
  "title": "Meu Mistério Estático v1",
  "slug": "meu_misterio_estatico_v1",
  "body": { ... cole aqui o JSON inteiro do arquivo .acassia-flow.json ... }
}
EOF
```

No PowerShell, é mais simples usar um arquivo:

```powershell
$doc = Get-Content -Raw -Encoding UTF8 "docs\templates\funil_estatico_meu_misterio_bloco1.acassia-flow.json" | ConvertFrom-Json
$body = @{ title = "Meu Mistério Estático v1"; slug = "meu_misterio_estatico_v1"; body = $doc } | ConvertTo-Json -Depth 50
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/flows/blueprints/import" -Method POST -ContentType "application/json; charset=utf-8" -Headers @{ "X-Acassia-Tenant" = "default" } -Body $body
```

Anote o `blueprint.id` retornado.

## 2) Obter o `lead_id` do seu número

Envie qualquer mensagem pelo WhatsApp para o número conectado (para criar/atualizar o lead), depois:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/leads?limit=30" -Headers @{ "X-Acassia-Tenant" = "default" }
```

Localize o lead pelo `telefone` e use o `id`.

## 3) Disparar o fluxo no Zap

```powershell
$bid = 1   # id retornado no import
$leadId = 42
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/flows/blueprints/$bid/execute" -Method POST -ContentType "application/json" -Headers @{ "X-Acassia-Tenant" = "default" } -Body (@{ lead_id = $leadId } | ConvertTo-Json)
```

Resposta esperada: `ok: true`, `queued_actions` > 0.

## O que você deve ver no celular

- Pausa inicial (~35 s), depois os balões do Bloco 1 (texto, link, imagem se o ficheiro existir e `PUBLIC_URL` estiver correto).
- Após os delays (incluindo 60 s e **4 min** antes do áudio), o PTT do Bloco 2 e os textos seguintes.

Se imagem ou áudio não chegarem, confira nos logs do app e valide no navegador se abre:

`%PUBLIC_URL%/assets/funil_estatico_meu_misterio/audio/bloco2_ptt.ogg`
