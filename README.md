# Invoice Enterprise Console

Enterprise-grade invoice management and automation platform — generates PDF invoices, automates scheduling, and delivers via email.

---

## Architecture

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4 | Dashboard UI |
| **Backend API** | FastAPI, Python 3.12, SQLAlchemy 2.0 | REST API, invoice engine |
| **Worker** | Celery 5.6 | Background job processing (email, PDF generation) |
| **Database** | PostgreSQL 16 | Persistent storage |
| **Cache/Broker** | Redis 7 | Celery message broker + caching |

---

## Quick Start (Local Development)

```bash
cd invoice-enterprise
docker compose up --build
```

This starts all services locally:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/api/docs

---

## Azure Deployment (One Command)

### Prerequisites

| Tool | Install |
|------|---------|
| **Azure CLI** | `curl -sL https://aka.ms/InstallAzureCLIDeb \| sudo bash` |
| **Terraform** | `brew install terraform` or [download](https://developer.hashicorp.com/terraform/install) |
| **Docker** | [Docker Desktop](https://docs.docker.com/get-docker/) |

### Deploy

```bash
# 1. Login to Azure
az login

# 2. Deploy everything with one command
cd infra/terraform/envs/deploy
chmod +x deploy.sh destroy.sh
./deploy.sh
```

**That's it.** The script will:
1. Check all prerequisites (Azure CLI, Terraform, Docker)
2. Create `terraform.tfvars` from your Azure context (prompts for DB password)
3. Register required Azure resource providers
4. Provision all infrastructure (Resource Group, ACR, PostgreSQL, Log Analytics, Container Apps Environment, Redis)
5. Build both Docker images and push to Azure Container Registry
6. Deploy all Container Apps (backend, frontend, celery worker)
7. Verify health and print the live URLs

### What Gets Created

| Resource | SKU/Tier | ~Monthly Cost |
|----------|----------|---------------|
| Resource Group | — | Free |
| Container Registry | Basic | ~$5 |
| PostgreSQL Flexible Server | Burstable B1ms | ~$12 |
| Log Analytics Workspace | PerGB2018 | ~$2 |
| Container Apps Environment | Consumption | Free tier |
| Container App: Backend | 0.5 vCPU / 1 GiB | ~$0* |
| Container App: Frontend | 0.25 vCPU / 0.5 GiB | ~$0* |
| Container App: Celery Worker | 0.25 vCPU / 0.5 GiB | ~$0* |
| Container App: Redis | 0.25 vCPU / 0.5 GiB | ~$0* |

\* Container Apps include a generous free grant (~180K vCPU-seconds/month).

**Estimated total: ~$19/month** (mostly PostgreSQL).

### Destroy (One Command)

```bash
cd infra/terraform/envs/deploy
./destroy.sh
```

This will:
1. Run `terraform destroy` to remove all 13 Azure resources
2. Safety-net: verify the resource group is gone (force-delete if orphaned)
3. Clean up local Docker images

**Zero orphan resources.** Your Azure account is completely clean after this.

### Emergency Cleanup

If `destroy.sh` fails or Terraform state is lost:

```bash
# Find and delete the resource group directly (deletes EVERYTHING inside it)
az group list --query "[?starts_with(name,'rg-invoice-deploy')].name" -o tsv \
  | xargs -I{} az group delete -n {} --yes --no-wait
```

---

## Standalone Invoice Generator (CLI)

The original CLI tool for quick invoice generation without the full enterprise stack.

### One-command auto mode

```bash
python3 invoice.py
```

Uses `contracts.sample.json`, today's date, writes PDFs to `generated_invoices/`.

### Quick 3-input mode

```bash
python3 invoice.py --quick
```

Prompts for: customer name, run date, total hours. Everything else from presets.

### With email delivery

```bash
python3 invoice.py --quick --send-email
```

### Full wizard

```bash
python3 invoice.py --wizard
```

### CLI flags

| Flag | Description |
|------|-------------|
| `--contracts-file FILE` | Path to contracts JSON |
| `--output-dir DIR` | Output directory for PDFs |
| `--run-date YYYY-MM-DD` | Override billing date |
| `--all` | Force all customers |
| `--no-auto` | Disable auto-fallback |
| `--send-email` | Send invoice via SMTP |

---

## API Documentation

When deployed, the API docs are available at:

| Endpoint | URL |
|----------|-----|
| Swagger UI | `{BACKEND_URL}/api/docs` |
| ReDoc | `{BACKEND_URL}/api/redoc` |
| OpenAPI JSON | `{BACKEND_URL}/api/openapi.json` |

### Key API Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/dashboard/stats` | Dashboard statistics |
| `POST` | `/api/invoices/run/quick` | Quick invoice generation |
| `POST` | `/api/invoices/run/wizard` | Wizard invoice generation |
| `GET` | `/api/customers/` | List customers |
| `GET` | `/api/vendors/` | List vendors |
| `GET` | `/api/logs/` | Audit logs |
| `POST` | `/api/smtp/test` | Test SMTP configuration |

---

## Project Structure

```
├── invoice.py                    # Standalone CLI invoice generator
├── contracts.sample.json         # Contract presets for CLI
├── infra/terraform/envs/deploy/  # Azure IaC (Terraform)
│   ├── deploy.sh                 # One-command deploy
│   ├── destroy.sh                # One-command destroy
│   ├── main.tf                   # All Azure resources
│   ├── variables.tf              # Input variables
│   ├── outputs.tf                # Output URLs
│   ├── providers.tf              # AzureRM provider config
│   └── versions.tf               # Terraform/provider versions
├── invoice-enterprise/           # Full enterprise application
│   ├── docker-compose.yml        # Local development
│   ├── backend/                  # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py           # App entrypoint
│   │   │   ├── api/routes/       # API route handlers
│   │   │   ├── core/             # Config, DB, security
│   │   │   ├── models/           # SQLAlchemy models
│   │   │   ├── schemas/          # Pydantic schemas
│   │   │   ├── services/         # Business logic
│   │   │   └── worker/           # Celery tasks
│   │   ├── alembic/              # DB migrations
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/                 # Next.js frontend
│       ├── src/app/              # App router pages
│       ├── src/components/       # React components
│       ├── src/lib/              # API client, utilities
│       ├── Dockerfile
│       └── package.json
└── docs/                         # Additional documentation
```

---

## Docker Hub Images

Pre-built images are available on Docker Hub:

```bash
docker pull sairam9479/invoice-enterprise-backend:v2.0.0
docker pull sairam9479/invoice-enterprise-frontend:v2.0.0
```

---

## License

Private repository.
