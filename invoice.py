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

    for customer in customers:
        frequency = customer.get("frequency", "monthly")
        schedule = customer.get("schedule", {})
        if not should_invoice_today(run_date, frequency, schedule):
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
    if send_email:
        print(f"Sent {emailed} invoice email(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate IT consulting invoices and optionally send by email.")
    parser.add_argument("--contracts-file", default="contracts.sample.json", help="Path to customer contracts JSON file")
    parser.add_argument("--output-dir", default="generated_invoices", help="Directory for generated PDF invoices")
    parser.add_argument("--run-date", default=date.today().isoformat(), help="Run date in YYYY-MM-DD")
    parser.add_argument("--send-email", action="store_true", help="Send generated invoices via SMTP")
    args = parser.parse_args()

    generate_and_optionally_send(
        contracts_file=Path(args.contracts_file),
        output_dir=Path(args.output_dir),
        run_date=parse_date(args.run_date),
        send_email=args.send_email,
    )
