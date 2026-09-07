# 🏗️ Acássia SaaS — Architecture Guide

> Quick reference for any developer joining the project.

## Stack

| Layer | Technology |
|---|---|
| **Backend** | Flask 3 + SQLAlchemy 2 + Gunicorn/gevent |
| **Frontend** | React 18 + TypeScript + Vite + React Router |
| **Database** | PostgreSQL 16 (prod) / SQLite (dev) |
| **Cache** | Redis 7 (Upstash in prod) |
| **AI** | Google Gemini 2.5 Flash via `google-genai` SDK |
| **Payments** | Stripe, Hotmart, Kiwify, Asaas, Mercado Pago Pix |
| **Infra** | Docker Compose + GitHub Actions CI |

## Directory Map

```
├── app.py                  # Flask application factory + blueprint registration
├── engine.py               # Core FSM engine (conversation state machine)
├── personalizer.py         # Gemini prompt builder (context stuffing)
├── config_cliente.py       # Client configuration loader (.env → dict)
├── inbox_manager.py        # Redis-backed message queue per lead
├── flow_executor.py        # Flow Builder runtime (DAG executor)
├── flow_graph_walk.py      # Graph DFS traversal for compiled flows
│
├── ai/                     # AI modules
│   ├── intent_classifier   # Lead intent detection
│   ├── sentiment_analyzer  # Urgency/crisis detection
│   ├── knowledge.py        # Static scripts (leitura fria, recovery)
│   ├── context_compressor  # Token-efficient history compression
│   └── stage_intelligence  # Per-node behavioral rules
│
├── api/                    # REST API layer
│   ├── saas/               # 63 endpoint modules (one per feature)
│   ├── admin/              # Super-admin endpoints
│   ├── tenant_config.py    # Multi-tenant config facade
│   └── routes/             # Legacy route helpers
│
├── db/
│   ├── models.py           # All SQLAlchemy models (~60 tables)
│   └── database.py         # Engine + SessionLocal factory
│
├── frontend/src/
│   ├── App.tsx             # Route definitions (53 lazy-loaded pages)
│   ├── builder/            # Flow Builder (Canvas, nodes, edges)
│   ├── inspector/          # Node configuration panels
│   ├── routes/             # Page components
│   ├── api/                # API client modules
│   └── components/         # Shared UI components
│
├── reliability/            # Infrastructure resilience
│   ├── redis_inbound.py    # Redis connection pool
│   ├── distributed_lock.py # Redis-based distributed locks
│   └── api_cache.py        # Redis response cache
│
├── webhooks/               # Inbound webhook processing
│   ├── meta.py             # WhatsApp Cloud API webhooks
│   ├── media.py            # Audio/image download + STT
│   └── idempotency.py      # Redis-based dedup
│
├── flows/                  # Static funnel definitions
│   ├── fase_1_saudacao/    # Greeting + data collection
│   └── fase_2_leitura/     # Reading + offer
│
├── tests/                  # 50 test files
├── alembic/                # Database migrations
└── docker-compose.yml      # PostgreSQL + Redis + App
```

## Key Patterns

### Multi-Tenancy
- Every table has `tenant_id` column
- `api/tenant_config.py` merges `.env` defaults with per-tenant overrides
- RLS (Row-Level Security) enforced at PostgreSQL level

### Message Processing Pipeline
```
WhatsApp Cloud API → webhook → Redis Inbound Queue
  → InboxManager (debounce + coalesce)
  → Engine (FSM state machine)
  → Personalizer (Gemini prompt)
  → WhatsApp Cloud API (response)
```

### AI Knowledge Injection (Context Stuffing)
```
AIKnowledgeFact (DB) → Redis cache → <BASE_DE_CONHECIMENTO> XML block
  → Injected before system prompt in every Gemini call
  → Anti-hallucination: "verdade absoluta do negócio"
```

### Flow Builder Runtime
```
FlowBlueprint (JSON graph) → flow_graph_walk.py (DFS)
  → Compiled step list → flow_executor.py (sequential exec)
  → Circuit breaker: 200 steps max + cycle detection + 120s timeout
```

## Running Locally

```bash
# Backend
pip install -r requirements.txt
cp env.example .env  # edit with your keys
python -c "from db.database import engine, Base; from db.models import *; Base.metadata.create_all(bind=engine)"
flask run --debug

# Frontend
cd frontend
npm install
npm run dev

# Full stack (Docker)
docker compose up -d
docker compose exec app alembic upgrade head
```

## Testing

```bash
pytest tests/ -v --tb=short
```

## Environment Variables

See `env.example` for the full list. Critical ones:
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis (Upstash) URL
- `GEMINI_API_KEY` — Google AI API key
- `META_TOKEN` — WhatsApp Cloud API token
- `FLASK_SECRET_KEY` — Session encryption
- `STRIPE_SECRET_KEY` — Payments
