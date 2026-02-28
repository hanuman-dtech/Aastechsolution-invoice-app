# User Guide

This guide explains typical workflows in the Invoice Enterprise Console.

## 1) Initial setup

1. Start stack (`docker-compose up -d --build`).
2. Run migrations (`docker-compose exec backend alembic upgrade head`).
3. Seed sample data (`docker-compose exec backend python -m scripts.seed_data`).
4. Open `http://localhost:3000`.

## 2) Manage vendors

Use Dashboard > Vendors to:
- create a vendor profile
- edit vendor billing/company details
- deactivate old vendors

## 3) Manage customers and payment terms

Use Dashboard > Customers to:
- create a customer under a vendor
- set contractor/service location details
- define per-customer payment terms (e.g., `Net 15`, `Monthly`)
- edit/deactivate customer records

Behavior note: customer creation auto-provisions a default contract and schedule so invoice generation works immediately.

## 4) Configure SMTP

Use Dashboard > Email Config to:
- add SMTP settings per vendor/use-case
- test connectivity with a target test email
- edit/deactivate SMTP configs

For local development, use Mailhog UI (`http://localhost:8025`) to inspect outgoing messages.

## 5) Generate invoices

Use Dashboard > Generator.

### Quick mode
Best for fast generation with default contract values.

### Wizard mode
Best for explicit control over date range and amounts.

Use **allow duplicate** only when you intentionally need another invoice for the same period.

### Scheduled mode
Run based on active customer schedule rules.

## 6) Work with generated invoices

Use Dashboard > Invoices to:
- list and filter invoices
- download invoice PDF
- resend invoice email
- view status changes

## 7) Monitor activity

Use:
- Dashboard cards/charts for high-level KPIs
- Execution Logs for run-level details and failures

## 8) Recommended operating rhythm

Daily:
- review failed runs and pending actions
- verify SMTP health when email failures rise

Weekly:
- validate schedules and contract rates
- reconcile invoice statuses (generated/sent/paid)
