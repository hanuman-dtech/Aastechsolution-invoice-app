# IT Consulting Invoice Automation

This script generates customer invoices based on per-customer billing frequency, hours, rates, and HST, and can optionally email PDFs to each customer.

## Files

- `invoice.py` - main generator + email dispatcher
- `contracts.sample.json` - sample customer contract/frequency configuration
- `.env.example` - SMTP placeholders template for email sending

## 1) Configure customer contracts

Edit `contracts.sample.json` with your real customers and terms.

Supported frequencies:

- `weekly`
- `biweekly`
- `monthly`

Schedule fields:

- Weekly: `billing_weekday` (0=Mon..6=Sun)
- Biweekly: `billing_weekday`, `anchor_date` (`YYYY-MM-DD`)
- Monthly: `billing_day` (1..31)

## 2) Generate invoices only (no email)

Run:

`python3 invoice.py --contracts-file contracts.sample.json --output-dir generated_invoices`

Optional run date override:

`python3 invoice.py --contracts-file contracts.sample.json --run-date 2026-03-01`

## 3) Generate and send emails

1. Copy `.env.example` to `.env` and update SMTP values.
2. Export env variables (Linux/macOS):

`set -a; source .env; set +a`

3. Run with `--send-email`:

`python3 invoice.py --contracts-file contracts.sample.json --send-email`

## Notes

- The script only generates invoices for customers whose frequency/schedule matches `run-date`.
- PDFs are attached to outbound emails.
- Monetary values are handled using `Decimal` with 2-decimal HALF_UP rounding.
