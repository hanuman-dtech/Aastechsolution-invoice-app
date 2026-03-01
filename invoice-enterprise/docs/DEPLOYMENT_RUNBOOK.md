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

### Production deployment (Docker Compose)

Use the production overlay to run immutable images and hardened container settings.

1. Copy `invoice-enterprise/.env.production.example` to `.env.production`.
2. Replace all placeholder secrets and domain values.
3. Pull immutable image tags.
4. Start with production compose file.
5. Run DB migrations once per release.

Recommended command sequence:

- `docker compose --env-file .env.production -f docker-compose.prod.yml pull`
- `docker compose --env-file .env.production -f docker-compose.prod.yml up -d`
- `docker compose --env-file .env.production -f docker-compose.prod.yml exec backend alembic upgrade head`

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

## 6) Production readiness controls implemented

- Separate production compose file: `docker-compose.prod.yml`
- Immutable image support via env-configurable tags
- Container hardening (`read_only`, `cap_drop: [ALL]`, `no-new-privileges`)
- Internal-only network segmentation for data services
- Required env var checks for secrets and public endpoints
- Build context minimization via backend/frontend `.dockerignore`

## 7) Manual work still required (operator checklist)

1. **TLS and ingress**
	- Put a reverse proxy/load balancer in front (Nginx/Traefik/Cloud LB).
	- Enforce HTTPS and HTTP->HTTPS redirect.

2. **Secrets management**
	- Move `.env.production` secrets to a vault (AWS/GCP/Azure secret manager, 1Password, etc.).
	- Rotate `SECRET_KEY`, `ENCRYPTION_KEY`, and SMTP credentials on a regular schedule.

3. **Database/Redis strategy**
	- Prefer managed PostgreSQL/Redis for production HA and backups.
	- Configure automated backups and tested restore runbooks.

4. **Observability and alerting**
	- Ship logs to a centralized system (ELK, Loki, Datadog, etc.).
	- Add alerts for `/health` failures, queue backlog, failed jobs, and SMTP errors.

5. **Security posture**
	- Add WAF/rate limiting at ingress.
	- Restrict admin account access and enforce strong password policy + MFA at identity layer.
	- Run image vulnerability scans in CI before release.

6. **Release governance**
	- Use immutable image tags in production (avoid deploying only `latest`).
	- Add CI gates: lint, type-check, tests, migration smoke test, image scan.

7. **Disaster recovery**
	- Document RPO/RTO targets.
	- Run restore drills at least quarterly.

## 8) Suggested production hardening

- Managed PostgreSQL and Redis
- HTTPS + reverse proxy
- Centralized logs and metrics
- Alerting on health checks, queue depth, and email failure rates
- Rate limiting and stricter auth/access controls
