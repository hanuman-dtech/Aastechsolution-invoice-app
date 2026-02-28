# IT Consulting Invoice Automation

Generate PDF invoices for consulting customers using preset contract data (hours/rate/HST/frequency), with optional SMTP email delivery.

## Project files

- `invoice.py` — main generator + interactive modes + optional email sender
- `contracts.sample.json` — vendor + customer contract presets
- `.env.example` — SMTP configuration template for email sending

## Configure contract presets

Edit `contracts.sample.json` with your real values.

Supported frequencies:

- `weekly`
- `biweekly`
- `monthly`

Schedule fields:

- Weekly: `billing_weekday` (`0=Mon .. 6=Sun`)
- Biweekly: `billing_weekday`, `anchor_date` (`YYYY-MM-DD`)
- Monthly: `billing_day` (`1..31`)

## Fastest ways to run

### 1) One-command auto mode

`python3 invoice.py`

Behavior:

- Uses `contracts.sample.json`
- Uses today's date
- Writes PDFs to `generated_invoices/`
- If no customer matches schedule, it automatically generates all customers (PDF only, no email)

### 2) Quick 3-input mode (your requested flow)

`python3 invoice.py --quick`

Prompts only:

1. Customer name
2. Run date (`YYYY-MM-DD`)
3. Total hours

Everything else comes from `contracts.sample.json` presets (rate, HST, address, fees, payment terms, etc.).

### 3) Full interactive wizard

`python3 invoice.py --wizard`

Guided options with format hints, including:

- contracts: scheduled customers only
- contracts: all customers
- single custom customer invoice

## Explicit CLI usage (advanced)

- Generate from contracts:
	- `python3 invoice.py --contracts-file contracts.sample.json --output-dir generated_invoices`
- Use specific run date:
	- `python3 invoice.py --run-date 2026-03-01`
- Force all customers:
	- `python3 invoice.py --all`
- Disable auto-fallback behavior:
	- `python3 invoice.py --no-auto`

## Email sending

1. Copy `.env.example` to `.env` and fill SMTP values.
2. Run:
	 - `python3 invoice.py --send-email`

Notes:

- `.env` is auto-loaded by the script.
- Email mode never auto-falls back to all customers; it follows schedule unless `--all` is provided.

## Notes

- Money values use `Decimal` with 2-digit HALF_UP rounding.
- Generated files are saved in `generated_invoices/` by default.
