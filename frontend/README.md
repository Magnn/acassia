# Cigana — Flow Builder (React)

Migração do Flow Builder do `dashboard.html` monolítico (25k linhas) para uma SPA isolada em React + TypeScript + Vite + React Flow.

## Pré-requisitos

- Node.js 20+ ([download](https://nodejs.org/en/download)). Recomendo a versão LTS atual.
- O backend Flask rodando em `http://localhost:5000` (para `npm run dev` proxiar `/api`).

## Setup inicial

```bash
cd frontend
npm install
```

## Desenvolvimento

```bash
npm run dev
```

Abre em `http://localhost:5173/builder/`. O Vite faz proxy de `/api`, `/media` e `/assets` para o Flask em `localhost:5000`.

> **Auth**: o cookie de sessão do flask-login viaja automaticamente porque o `client.ts` usa `credentials: 'include'`. Para ver fluxos reais, faça login no Flask em outra aba antes.

## Build de produção

```bash
npm run build
```

Gera `frontend/dist/`. O Flask serve esse diretório em `/builder/*` (ver `app.py` → `render_builder_spa`).

## Estrutura (Fase 0)

```
frontend/
├── package.json
├── vite.config.ts          # base /builder/, proxy de /api em dev
├── tsconfig.json           # strict + paths
├── tailwind.config.ts      # paleta cigana-* espelhando o dashboard.html
├── index.html
└── src/
    ├── main.tsx            # React + Router + TanStack Query
    ├── App.tsx             # shell com header + <Routes>
    ├── index.css           # diretivas Tailwind
    ├── api/
    │   ├── client.ts       # fetch wrapper, credentials: 'include'
    │   └── blueprints.ts   # GET /api/flows/blueprints (tipado)
    └── routes/
        └── BlueprintsList.tsx  # primeira tela: lista os blueprints reais
```

## Roadmap

- **Fase 0**: andaime + lista de blueprints ✅
- **Fase 1**: canvas read-only com React Flow ✅
- **Fase 2**: edição com paleta DnD + auto-save debounceado ✅
- **Fase 3**: inspetores por tipo de nó ✅
- **Fase 3.1**: Conteúdo multi-passos + Rule Builder completo + upload de mídia ✅
- **Fase 4a**: lint visual do grafo ✅
- **Fase 4b** (atual): simulador WhatsApp com persona ✅
- **Fase 5**: feature flag, redirect de `/dashboard` para `/builder`
- **Fase 6**: descomissionar `dashboard.html`

Ver [docs/roadmap-canvas-orbita.md](../docs/roadmap-canvas-orbita.md) para o contexto maior.
