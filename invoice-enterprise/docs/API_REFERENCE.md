# API Reference

Base URL: `http://localhost:8000`

API prefix: `/api`

## Health

- `GET /health` — service liveness
- `GET /health/ready` — readiness (includes DB connectivity)

## Dashboard (`/api/dashboard`)

- `GET /stats`
- `GET /upcoming-invoices?days_ahead=14`
- `GET /recent-activity?limit=10`
- `GET /revenue-by-month?months=6`

## Customers (`/api/customers`)

- `GET /customers?vendor_id=&active_only=true`
- `GET /customers/{customer_id}`
- `POST /customers`
- `PATCH /customers/{customer_id}`
- `DELETE /customers/{customer_id}` (soft delete)

### Contract sub-routes

- `POST /customers/{customer_id}/contract`
- `PATCH /customers/{customer_id}/contract`

### Schedule sub-routes

- `POST /customers/{customer_id}/schedule`
- `PATCH /customers/{customer_id}/schedule`
- `POST /customers/{customer_id}/schedule/toggle`
- `GET /customers/{customer_id}/next-invoice-preview`

## Vendors (`/api/vendors`)

- `GET /vendors?active_only=true`
- `GET /vendors/{vendor_id}`
- `POST /vendors`
- `PATCH /vendors/{vendor_id}`
- `DELETE /vendors/{vendor_id}` (soft delete)

## SMTP Configurations (`/api/smtp-configs`)

- `GET /smtp-configs?vendor_id=&active_only=true`
- `GET /smtp-configs/{config_id}`
- `POST /smtp-configs`
- `PATCH /smtp-configs/{config_id}`
- `DELETE /smtp-configs/{config_id}` (soft delete)
- `POST /smtp-configs/{config_id}/test?test_email=<address>`

## Invoices (`/api/invoices`)

### Generation routes

- `POST /invoices/run/quick`
- `POST /invoices/run/wizard`
- `POST /invoices/run/scheduled`
- `POST /invoices/run/generate-all?run_date=<YYYY-MM-DD>&send_email=false`
- `POST /invoices/run/manual-override`

### Data and actions

- `GET /invoices?page=1&per_page=20&customer_id=&status=&start_date=&end_date=`
- `GET /invoices/{invoice_id}`
- `GET /invoices/{invoice_id}/download`
- `POST /invoices/{invoice_id}/resend-email`
- `PATCH /invoices/{invoice_id}/status?new_status=<status>`

## Execution Logs (`/api/execution-logs`)

- `GET /execution-logs?page=1&per_page=20&mode=&start_date=&end_date=`
- `GET /execution-logs/{log_id}`
- `GET /execution-logs/stats/summary?days=30`

## Notes for Integrators

- The canonical API surface is the backend OpenAPI page at `GET /api/docs`.
- Most list endpoints support query filters and/or pagination.
- Delete operations are soft deletes for core business entities.
- Read and write DTOs are defined under `backend/app/schemas`.
