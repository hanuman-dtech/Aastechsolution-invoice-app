import argparse
import json
import os
import smtplib
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


MONEY_QUANT = Decimal("0.01")


def load_env_file(env_path: Path = Path(".env")) -> None:
    """Load KEY=VALUE pairs from .env into process environment if not already set."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def prompt_text(label: str, default: str | None = None, required: bool = True, format_hint: str | None = None) -> str:
    hint = f" [{default}]" if default is not None else ""
    fmt = f" ({format_hint})" if format_hint else ""
    while True:
        value = input(f"{label}{fmt}{hint}: ").strip()
        if not value and default is not None:
            return default
        if value or not required:
            return value
        print("This field is required.")


def prompt_date(label: str, default: str) -> date:
    while True:
        value = prompt_text(label, default=default, format_hint="YYYY-MM-DD")
        try:
            return parse_date(value)
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD (example: 2026-03-01).")


def prompt_decimal(label: str, default: str) -> Decimal:
    while True:
        value = prompt_text(label, default=default, format_hint="number (example: 45 or 45.00)")
        try:
            return to_decimal(value)
        except Exception:
            print("Invalid number. Example valid inputs: 40, 40.5, 40.00")


def prompt_int(label: str, default: int, min_value: int | None = None, max_value: int | None = None) -> int:
    while True:
        raw = prompt_text(label, default=str(default))
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue

        if min_value is not None and value < min_value:
            print(f"Value must be >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Value must be <= {max_value}.")
            continue
        return value


def prompt_choice(label: str, options: list[str], default_index: int = 1) -> str:
    print(f"\n{label}")
    for idx, option in enumerate(options, start=1):
        default_mark = " (default)" if idx == default_index else ""
        print(f"  {idx}) {option}{default_mark}")

    while True:
        selected = prompt_text("Choose option number", default=str(default_index), format_hint=f"1..{len(options)}")
        try:
            selected_idx = int(selected)
            if 1 <= selected_idx <= len(options):
                return options[selected_idx - 1]
        except ValueError:
            pass
        print(f"Please choose a valid option number between 1 and {len(options)}.")


def prompt_yes_no(label: str, default_yes: bool = True) -> bool:
    default = "Y" if default_yes else "N"
    while True:
        raw = prompt_text(label, default=default, format_hint="Y/N").lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Please answer Y or N.")


def collect_multiline(label: str) -> list[str]:
    print(f"\n{label}")
    print("Enter one line at a time. Press Enter on an empty line to finish.")
    lines: list[str] = []
    while True:
        line = input(f"  Line {len(lines) + 1}: ").strip()
        if not line:
            break
        lines.append(line)
    if not lines:
        print("No lines entered. Using one blank line.")
        lines.append("")
    return lines


def find_customer_by_name(customers: list[dict], customer_name: str) -> dict | None:
    normalized = customer_name.strip().lower()
    for customer in customers:
        if customer.get("name", "").strip().lower() == normalized:
            return customer
    return None


def to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value) -> str:
    """Format Decimal as money with 2 decimal places."""
    return f"{to_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)}"


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_date(value: date) -> str:
    return value.strftime("%b %d, %Y")


def compute_billing_period(run_date: date, frequency: str) -> tuple[date, date]:
    """
    Return (period_start, period_end) for the invoice to generate on run_date.
    Frequency supports: weekly, biweekly, monthly.
    """
    frequency = frequency.lower()
    period_end = run_date - timedelta(days=1)

    if frequency == "weekly":
        period_start = period_end - timedelta(days=6)
    elif frequency == "biweekly":
        period_start = period_end - timedelta(days=13)
    elif frequency == "monthly":
        first_of_current_month = run_date.replace(day=1)
        period_end = first_of_current_month - timedelta(days=1)
        period_start = period_end.replace(day=1)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")

    return period_start, period_end


def should_invoice_today(run_date: date, frequency: str, schedule: dict) -> bool:
    """
    Determine whether invoice should be generated for a contract on run_date.
    schedule fields:
      - weekly/biweekly: billing_weekday (0=Mon..6=Sun)
      - biweekly: anchor_date (YYYY-MM-DD)
      - monthly: billing_day (1..28/31)
    """
    frequency = frequency.lower()

    if frequency == "weekly":
        billing_weekday = int(schedule.get("billing_weekday", 4))  # default Friday
        return run_date.weekday() == billing_weekday

    if frequency == "biweekly":
        billing_weekday = int(schedule.get("billing_weekday", 4))
        anchor_date = parse_date(schedule.get("anchor_date", "2026-01-02"))
        return run_date.weekday() == billing_weekday and ((run_date - anchor_date).days % 14 == 0)

    if frequency == "monthly":
        billing_day = int(schedule.get("billing_day", 1))
        return run_date.day == billing_day

    raise ValueError(f"Unsupported frequency: {frequency}")


def generate_invoice_pdf(
    filename: str,
    invoice_number: str,
    invoice_date: str,
    vendor_name: str,
    vendor_email: str,
    vendor_address_lines: Iterable[str],
    vendor_hst_number: str,
    contractor_name: str,
    customer_name: str,
    customer_address_lines: Iterable[str],
    service_location: str,
    period_start: str,
    period_end: str,
    total_hours: Decimal,
    rate_per_hour: Decimal,
    hst_rate: Decimal = Decimal("0.13"),
    payment_terms: str = "Biweekly",
    extra_fees: Decimal = Decimal("0.00"),
    extra_fees_label: str = "Other Fees",
):
    total_hours = to_decimal(total_hours)
    rate_per_hour = to_decimal(rate_per_hour)
    hst_rate = to_decimal(hst_rate)
    extra_fees = to_decimal(extra_fees)

    # Calculate amounts
    labor_subtotal = total_hours * rate_per_hour
    subtotal = labor_subtotal + extra_fees
    hst_amount = (subtotal * hst_rate).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total = subtotal + hst_amount

    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    left_margin = 20 * mm
    right_margin = width - 20 * mm
    y = height - 30 * mm

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, y, "INVOICE")
    y -= 15 * mm

    # Header labels
    c.setFont("Helvetica-Bold", 10)
    header_y = y
    c.drawString(left_margin, header_y, "Billed to:")

    header_text = "COMPANY INFORMATION:"
    c.drawRightString(right_margin, header_y, header_text)
    header_left_x = right_margin - c.stringWidth(header_text, "Helvetica-Bold", 10)

    y = header_y - 5 * mm

    # Customer block (left)
    customer_y = y
    c.setFont("Helvetica", 10)
    c.drawString(left_margin, customer_y, customer_name)
    customer_y -= 5 * mm
    for line in customer_address_lines:
        c.drawString(left_margin, customer_y, line)
        customer_y -= 5 * mm

    # Vendor block (right)
    vendor_x = header_left_x
    vendor_y = y
    c.drawString(vendor_x, vendor_y, vendor_name)
    vendor_y -= 5 * mm
    for line in vendor_address_lines:
        c.drawString(vendor_x, vendor_y, line)
        vendor_y -= 5 * mm
    c.drawString(vendor_x, vendor_y, f"H.S.T. #: {vendor_hst_number}")

    y = min(customer_y, vendor_y) - 10 * mm

    # Metadata block
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin, y, f"Contractor Name: {contractor_name}")
    c.drawRightString(right_margin, y, f"Date: {invoice_date}")
    y -= 6 * mm
    c.drawRightString(right_margin, y, f"Invoice #: {invoice_number}")
    y -= 10 * mm

    c.drawString(left_margin, y, f"For services rendered at: {service_location}")
    c.drawRightString(right_margin, y, f"Payment Terms: {payment_terms}")
    y -= 8 * mm
    c.drawString(left_margin, y, f"For the period: {period_start} to {period_end}")
    y -= 12 * mm

    # Totals box
    c.setLineWidth(1)
    box_top = y
    box_left = left_margin
    box_right = right_margin
    box_bottom = box_top - 66 * mm
    c.rect(box_left, box_bottom, box_right - box_left, box_top - box_bottom, stroke=1, fill=0)

    inner_y = box_top - 8 * mm
    inner_x_label = box_left + 5 * mm
    inner_x_value = box_right - 5 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(inner_x_label, inner_y, "Timesheet:")
    inner_y -= 8 * mm

    c.drawString(inner_x_label, inner_y, "Total Hours:")
    c.setFont("Helvetica", 10)
    c.drawRightString(inner_x_value, inner_y, f"{money(total_hours)}")
    inner_y -= 6 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(inner_x_label, inner_y, "Rate / Hour:")
    c.setFont("Helvetica", 10)
    c.drawRightString(inner_x_value, inner_y, f"${money(rate_per_hour)}")
    inner_y -= 6 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(inner_x_label, inner_y, "Labor Fees:")
    c.setFont("Helvetica", 10)
    c.drawRightString(inner_x_value, inner_y, f"${money(labor_subtotal)}")
    inner_y -= 6 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(inner_x_label, inner_y, f"{extra_fees_label}:")
    c.setFont("Helvetica", 10)
    c.drawRightString(inner_x_value, inner_y, f"${money(extra_fees)}")
    inner_y -= 6 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(inner_x_label, inner_y, "Subtotal:")
    c.setFont("Helvetica", 10)
    c.drawRightString(inner_x_value, inner_y, f"${money(subtotal)}")
    inner_y -= 6 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(inner_x_label, inner_y, f"H.S.T. ({int(hst_rate * 100)}%):")
    c.setFont("Helvetica", 10)
    c.drawRightString(inner_x_value, inner_y, f"${money(hst_amount)}")
    inner_y -= 8 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(inner_x_label, inner_y, "INVOICE TOTAL:")
    c.drawRightString(inner_x_value, inner_y, f"${money(total)}")

    # Footer
    y_footer = box_bottom - 15 * mm
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y_footer, "If you have any questions about this invoice, please contact:")
    y_footer -= 5 * mm
    c.drawString(left_margin, y_footer, f"{vendor_name} | {vendor_email}")

    c.showPage()
    c.save()

    print("Invoice PDF generated at:", str(output_path.resolve()))


def send_invoice_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    customer_email: str,
    subject: str,
    body: str,
    attachment_path: Path,
):
    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = customer_email
    msg["Subject"] = subject
    msg.set_content(body)

    pdf_bytes = attachment_path.read_bytes()
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=attachment_path.name)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)


def generate_and_optionally_send(
    contracts_file: Path,
    output_dir: Path,
    run_date: date,
    send_email: bool,
    ignore_schedule: bool,
):
    config = json.loads(contracts_file.read_text(encoding="utf-8"))
    vendor = config["vendor"]
    customers = config["customers"]

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", vendor.get("email", ""))

    generated = 0
    emailed = 0
    skipped: list[tuple[str, str, dict]] = []

    for customer in customers:
        frequency = customer.get("frequency", "monthly")
        schedule = customer.get("schedule", {})
        if not ignore_schedule and not should_invoice_today(run_date, frequency, schedule):
            skipped.append((customer.get("name", "Unknown customer"), frequency, schedule))
            continue

        period_start, period_end = compute_billing_period(run_date, frequency)
        total_hours = to_decimal(customer.get("hours", "0"))
        rate_per_hour = to_decimal(customer.get("rate_per_hour", "0"))
        hst_rate = to_decimal(customer.get("hst_rate", "0.13"))
        extra_fees = to_decimal(customer.get("extra_fees", "0.00"))
        extra_fees_label = customer.get("extra_fees_label", "Other Fees")

        invoice_number = f"{customer.get('invoice_prefix', 'INV')}-{run_date.strftime('%Y%m%d')}-{generated+1:03d}"
        filename = output_dir / f"{invoice_number}.pdf"

        generate_invoice_pdf(
            filename=str(filename),
            invoice_number=invoice_number,
            invoice_date=run_date.strftime("%d/%m/%Y"),
            vendor_name=vendor["name"],
            vendor_email=vendor["email"],
            vendor_address_lines=vendor["address_lines"],
            vendor_hst_number=vendor["hst_number"],
            contractor_name=customer.get("contractor_name", vendor.get("default_contractor", "Contractor")),
            customer_name=customer["name"],
            customer_address_lines=customer["address_lines"],
            service_location=customer.get("service_location", "Ontario, Canada"),
            period_start=format_date(period_start),
            period_end=format_date(period_end),
            total_hours=total_hours,
            rate_per_hour=rate_per_hour,
            hst_rate=hst_rate,
            payment_terms=customer.get("payment_terms", "Monthly"),
            extra_fees=extra_fees,
            extra_fees_label=extra_fees_label,
        )
        generated += 1

        if send_email:
            if not smtp_host:
                raise RuntimeError("SMTP_HOST is required when --send-email is used")
            subject = f"Invoice {invoice_number} - {vendor['name']}"
            body = (
                f"Hello {customer['name']},\n\n"
                f"Please find attached invoice {invoice_number} for period {format_date(period_start)} to {format_date(period_end)}.\n\n"
                f"Regards,\n{vendor['name']}"
            )
            send_invoice_email(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                smtp_from=smtp_from,
                customer_email=customer["email"],
                subject=subject,
                body=body,
                attachment_path=filename,
            )
            emailed += 1

    print(f"Generated {generated} invoice(s) for run date {run_date.isoformat()}.")
    if generated == 0:
        print("No invoices matched today's schedule.")
        print(
            "Tip: use --run-date YYYY-MM-DD for a billing day or pass --ignore-schedule to force generation for all customers."
        )
        if skipped:
            print("Skipped customers:")
            for customer_name, frequency, schedule in skipped:
                print(f"  - {customer_name}: frequency={frequency}, schedule={schedule}")

    if send_email:
        print(f"Sent {emailed} invoice email(s).")

    return {
        "generated": generated,
        "emailed": emailed,
        "skipped": skipped,
    }


def run_interactive_wizard() -> None:
    print("\n=== Invoice Wizard (Q&A mode) ===")
    print("We'll ask questions and generate invoices with your answers.")

    mode = prompt_choice(
        "What do you want to generate?",
        [
            "From contracts file (scheduled customers only)",
            "From contracts file (all customers)",
            "Single custom customer invoice",
        ],
        default_index=1,
    )

    run_date = prompt_date("Run date", default=date.today().isoformat())
    output_dir = Path(prompt_text("Output folder", default="generated_invoices"))

    if mode.startswith("From contracts file"):
        contracts_file = Path(prompt_text("Contracts file path", default="contracts.sample.json"))
        send_email = prompt_yes_no("Send email after generation?", default_yes=False)
        ignore_schedule = "all customers" in mode

        if send_email and not os.getenv("SMTP_HOST"):
            print("\nSMTP_HOST is not configured. Add SMTP values in .env first for email sending.")
            send_email = False

        result = generate_and_optionally_send(
            contracts_file=contracts_file,
            output_dir=output_dir,
            run_date=run_date,
            send_email=send_email,
            ignore_schedule=ignore_schedule,
        )

        if result["generated"] == 0 and not ignore_schedule:
            if prompt_yes_no("No matches found. Generate all customers now?", default_yes=True):
                generate_and_optionally_send(
                    contracts_file=contracts_file,
                    output_dir=output_dir,
                    run_date=run_date,
                    send_email=False,
                    ignore_schedule=True,
                )
        return

    # Single custom invoice mode
    print("\nProvide vendor/company details")
    vendor_name = prompt_text("Vendor name", default="AAS Tech Solutions Corp")
    vendor_email = prompt_text("Vendor email", default="contact@aastechsolutions.com")
    vendor_hst = prompt_text("Vendor HST number", default="733392369RT0001")
    vendor_address_lines = collect_multiline("Vendor address lines")

    print("\nProvide customer details")
    customer_name = prompt_text("Customer name")
    customer_email = prompt_text("Customer email", required=False)
    customer_address_lines = collect_multiline("Customer address lines")
    contractor_name = prompt_text("Contractor name", default="Anusha Veeramalla")
    service_location = prompt_text("Service location", default="Ontario, Canada")
    invoice_prefix = prompt_text("Invoice prefix", default="INV")

    frequency = prompt_choice("Billing frequency", ["weekly", "biweekly", "monthly"], default_index=3)
    period_start, period_end = compute_billing_period(run_date, frequency)

    print("\nProvide billing amounts")
    total_hours = prompt_decimal("Total hours", default="40.00")
    rate_per_hour = prompt_decimal("Rate per hour", default="45.00")
    hst_rate = prompt_decimal("HST rate", default="0.13")
    extra_fees = prompt_decimal("Extra fees", default="0.00")
    extra_fees_label = prompt_text("Extra fees label", default="Other Fees")
    payment_terms = prompt_text("Payment terms", default=frequency.title())

    invoice_number = f"{invoice_prefix}-{run_date.strftime('%Y%m%d')}-001"
    filename = output_dir / f"{invoice_number}.pdf"

    generate_invoice_pdf(
        filename=str(filename),
        invoice_number=invoice_number,
        invoice_date=run_date.strftime("%d/%m/%Y"),
        vendor_name=vendor_name,
        vendor_email=vendor_email,
        vendor_address_lines=vendor_address_lines,
        vendor_hst_number=vendor_hst,
        contractor_name=contractor_name,
        customer_name=customer_name,
        customer_address_lines=customer_address_lines,
        service_location=service_location,
        period_start=format_date(period_start),
        period_end=format_date(period_end),
        total_hours=total_hours,
        rate_per_hour=rate_per_hour,
        hst_rate=hst_rate,
        payment_terms=payment_terms,
        extra_fees=extra_fees,
        extra_fees_label=extra_fees_label,
    )

    if prompt_yes_no("Email this invoice now?", default_yes=False):
        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", vendor_email)

        if not smtp_host:
            print("Cannot send email: SMTP_HOST not configured in .env")
            return
        if not customer_email:
            print("Cannot send email: customer email is empty.")
            return

        subject = f"Invoice {invoice_number} - {vendor_name}"
        body = (
            f"Hello {customer_name},\n\n"
            f"Please find attached invoice {invoice_number} for period {format_date(period_start)} to {format_date(period_end)}.\n\n"
            f"Regards,\n{vendor_name}"
        )

        send_invoice_email(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_from=smtp_from,
            customer_email=customer_email,
            subject=subject,
            body=body,
            attachment_path=filename,
        )
        print(f"Email sent to: {customer_email}")


def run_quick_customer_mode(contracts_file: Path, output_dir: Path) -> None:
    """Prompt only for customer name, run date, and hours; use all other fields from contract presets."""
    config = json.loads(contracts_file.read_text(encoding="utf-8"))
    vendor = config["vendor"]
    customers = config["customers"]

    print("\n=== Quick Invoice Mode (3 inputs) ===")
    print("Only provide: customer name, run date, and hours.")

    while True:
        customer_name = prompt_text("Customer name", required=True)
        customer = find_customer_by_name(customers, customer_name)
        if customer:
            break
        print("Customer not found. Available customers:")
        for c in customers:
            print(f"  - {c.get('name', 'Unknown')}")

    run_date = prompt_date("Run date", default=date.today().isoformat())
    total_hours = prompt_decimal("Total hours", default=str(customer.get("hours", "40.00")))

    frequency = customer.get("frequency", "monthly")
    period_start, period_end = compute_billing_period(run_date, frequency)
    rate_per_hour = to_decimal(customer.get("rate_per_hour", "0"))
    hst_rate = to_decimal(customer.get("hst_rate", "0.13"))
    extra_fees = to_decimal(customer.get("extra_fees", "0.00"))
    extra_fees_label = customer.get("extra_fees_label", "Other Fees")

    invoice_number = f"{customer.get('invoice_prefix', 'INV')}-{run_date.strftime('%Y%m%d')}-001"
    filename = output_dir / f"{invoice_number}.pdf"

    generate_invoice_pdf(
        filename=str(filename),
        invoice_number=invoice_number,
        invoice_date=run_date.strftime("%d/%m/%Y"),
        vendor_name=vendor["name"],
        vendor_email=vendor["email"],
        vendor_address_lines=vendor["address_lines"],
        vendor_hst_number=vendor["hst_number"],
        contractor_name=customer.get("contractor_name", vendor.get("default_contractor", "Contractor")),
        customer_name=customer["name"],
        customer_address_lines=customer["address_lines"],
        service_location=customer.get("service_location", "Ontario, Canada"),
        period_start=format_date(period_start),
        period_end=format_date(period_end),
        total_hours=total_hours,
        rate_per_hour=rate_per_hour,
        hst_rate=hst_rate,
        payment_terms=customer.get("payment_terms", frequency.title()),
        extra_fees=extra_fees,
        extra_fees_label=extra_fees_label,
    )

    print("\nQuick mode complete ✅")
    print(f"Customer: {customer['name']}")
    print(f"Run date: {run_date.isoformat()}")
    print(f"Hours used: {money(total_hours)}")
    print(f"Output file: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate IT consulting invoices and optionally send by email.")
    parser.add_argument("-c", "--contracts-file", default="contracts.sample.json", help="Path to customer contracts JSON file")
    parser.add_argument("-o", "--output-dir", default="generated_invoices", help="Directory for generated PDF invoices")
    parser.add_argument("-d", "--run-date", default=date.today().isoformat(), help="Run date in YYYY-MM-DD")
    parser.add_argument("-w", "--wizard", action="store_true", help="Interactive Q&A mode with guided options")
    parser.add_argument("-q", "--quick", action="store_true", help="Quick prompt mode: customer name + run date + hours")
    parser.add_argument("--ignore-schedule", "--all", action="store_true", help="Generate for all customers regardless of schedule")
    parser.add_argument("--send-email", "--email", action="store_true", help="Send generated invoices via SMTP")
    parser.add_argument(
        "--no-auto",
        action="store_true",
        help="Disable automatic fallback to generate all when schedule produces zero invoices (email mode never auto-falls back)",
    )
    args = parser.parse_args()

    load_env_file(Path(".env"))

    if args.quick:
        run_quick_customer_mode(Path(args.contracts_file), Path(args.output_dir))
        raise SystemExit(0)

    if args.wizard:
        run_interactive_wizard()
        raise SystemExit(0)

    result = generate_and_optionally_send(
        contracts_file=Path(args.contracts_file),
        output_dir=Path(args.output_dir),
        run_date=parse_date(args.run_date),
        send_email=args.send_email,
        ignore_schedule=args.ignore_schedule,
    )

    should_auto_fallback = (
        not args.no_auto
        and not args.send_email
        and not args.ignore_schedule
        and result["generated"] == 0
    )

    if should_auto_fallback:
        print("Running automatic fallback: generating invoices for all customers...")
        generate_and_optionally_send(
            contracts_file=Path(args.contracts_file),
            output_dir=Path(args.output_dir),
            run_date=parse_date(args.run_date),
            send_email=False,
            ignore_schedule=True,
        )
