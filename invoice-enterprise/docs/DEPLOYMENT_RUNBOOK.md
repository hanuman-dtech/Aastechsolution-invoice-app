# Deployment & Operations Runbook

## Scope

This runbook covers local/container deployment, health validation, and common recovery actions.

## 1) Deploy/update

From `invoice-enterprise/`:

1. Build + start services.
2. Apply migrations.
3. Seed data for non-production environments as needed.

Primary services:
- `postgres`
- `redis`
- `backend`
- `frontend`
- `celery-worker`
- `celery-beat`
- `mailhog` (dev only)

## 2) Validate after deploy

### Service state
- Check container status via compose.

### Health checks
- `GET /health` should return `status: healthy`.
- `GET /health/ready` should return `status: ready` and `database: connected`.

### App URLs
- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/api/docs`
- Mailhog: `http://localhost:8025`

## 3) Operational checks

- Create/update a customer (including payment terms).
- Run quick mode invoice generation.
- Download generated PDF.
- Resend email and verify in Mailhog or SMTP target inbox.

## 4) Troubleshooting

## Backend not healthy

- Inspect backend logs.
- Verify DB credentials and network connectivity.
- Ensure migrations are applied.

## Frontend cannot reach API

- Verify `NEXT_PUBLIC_API_URL` points to backend host.
- Confirm backend is serving `/api` routes.

## Email send failures

- Validate SMTP credentials/port/TLS.
- Test SMTP config from API/UI.
- For dev, confirm Mailhog is up and mapped to SMTP host/port.

## Duplicate invoice errors

- By default duplicate billing periods are blocked.
- In wizard mode, set allow-duplicate only when intentional.

## 5) Data safety and environment guidance

- Keep production secrets out of source control.
- Rotate SMTP/API secrets if previously exposed.
- Back up PostgreSQL volumes before major upgrades.

## 6) Suggested production hardening

- Managed PostgreSQL and Redis
- HTTPS + reverse proxy
- Centralized logs and metrics
- Alerting on health checks, queue depth, and email failure rates
- Rate limiting and stricter auth/access controls
