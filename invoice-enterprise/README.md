# Invoice Enterprise Console

Enterprise-ready invoice automation platform built with **FastAPI + Next.js + PostgreSQL + Redis + Celery**.

This repository provides a complete local SaaS-style invoice workflow:
- customer/vendor management
- contract + billing schedule automation
- invoice PDF generation
- SMTP-based email delivery
- execution history and dashboard analytics

## Documentation Index

- `README.md` (this file): architecture, setup, quick reference
- `docs/USER_GUIDE.md`: day-to-day product operations by feature
- `docs/API_REFERENCE.md`: endpoint-level backend API reference
- `docs/DEPLOYMENT_RUNBOOK.md`: deploy, operate, and recover

## Key Capabilities

- **Dashboard & Insights**
  - monthly revenue
  - upcoming invoices
  - recent generation activity
- **Customer Lifecycle**
  - create/update/deactivate customers
  - auto-create default contract + schedule on customer creation
  - per-customer payment terms support
- **Vendor + SMTP Management**
  - CRUD vendors
  - CRUD SMTP configurations
  - SMTP test delivery endpoint
- **Invoice Generation Modes**
  - quick mode
  - wizard mode (with duplicate-period override)
  - scheduled mode (batch)
  - manual date override
- **Invoice Operations**
  - paginated listing with filters
  - PDF download
  - resend email
  - status update
- **Background Processing**
  - Celery worker for async tasks
  - Celery beat for recurring schedule runs

## Architecture at a Glance

```text
Frontend (Next.js:3000)
  -> Backend API (FastAPI:8000, prefix /api)
    -> PostgreSQL (data)
    -> Redis (queue/cache)
    -> Celery Worker/Beat (async jobs + scheduling)
    -> Mailhog or SMTP provider (email delivery)
```

## Stack

### Backend
- Python 3.12
- FastAPI (async)
- SQLAlchemy 2 async + asyncpg
- Alembic migrations
- Celery + Redis
- ReportLab PDF generation
- Pydantic v2

### Frontend
- Next.js 14 App Router
- React 18 + TypeScript
- TailwindCSS + Radix/shadcn-style UI components
- TanStack React Query

### Infrastructure
- Docker Compose
- PostgreSQL 16
- Redis 7
- Mailhog (dev email sink)

## Quick Start (Docker)

### Prerequisites
- Docker + Docker Compose
- Git

### 1) Start services

```bash
cd invoice-enterprise
docker-compose up -d --build
```

### 2) Run database migrations

```bash
docker-compose exec backend alembic upgrade head
```

### 3) Seed demo data

```bash
docker-compose exec backend python -m scripts.seed_data
```

### 4) Open the app

- Frontend: `http://localhost:3000`
- Backend root: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/api/docs`
- Mailhog UI: `http://localhost:8025`

### Demo Accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@invoiceenterprise.local` | `admin123` |
| Viewer | `viewer@invoiceenterprise.local` | `viewer123` |

## Local (Non-Docker) Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Celery (optional for local async)

```bash
cd backend
celery -A app.worker.tasks worker --loglevel=info
celery -A app.worker.tasks beat --loglevel=info
```

## Environment Variables

### Backend (`backend/.env`)

Use `backend/.env.example` as baseline.

Important keys:
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `ENCRYPTION_KEY`
- `CORS_ORIGINS`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`

### Frontend
- `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`)

## API Prefix and Health Endpoints

- API base prefix: `/api`
- Health: `GET /health`
- Readiness: `GET /health/ready`

Full endpoint matrix is maintained in `docs/API_REFERENCE.md`.

## Project Layout

```text
invoice-enterprise/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # customers, invoices, vendors, smtp, dashboard, logs
│   │   ├── core/                # config, database, security, logging
│   │   ├── models/              # ORM models
│   │   ├── schemas/             # request/response schemas
│   │   └── services/            # invoice engine, PDF/email services
│   ├── alembic/                 # db migrations
│   ├── scripts/seed_data.py     # demo data seeding
│   └── requirements.txt
├── frontend/
│   ├── src/app/dashboard/       # dashboard pages
│   ├── src/components/          # reusable UI
│   ├── src/lib/api.ts           # API client
│   └── src/types/               # app types
├── docs/
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT_RUNBOOK.md
│   └── USER_GUIDE.md
├── docker-compose.yml
└── README.md
```

## Operational Notes

- SMTP credentials are encrypted at rest in the DB.
- Customer creation automatically creates a default contract and schedule.
- Payment terms can be set/updated per customer.
- Wizard generation can optionally allow duplicate invoices for existing periods.

## Troubleshooting Quick Hits

- Backend unhealthy: check `docker-compose logs backend` and DB connectivity.
- Frontend API errors: verify `NEXT_PUBLIC_API_URL` and backend `/api` prefix.
- No emails received: verify SMTP config and inspect Mailhog in dev.

Detailed recovery steps are in `docs/DEPLOYMENT_RUNBOOK.md`.

## License

MIT (add `LICENSE` file if you need explicit legal text in this repository root).
