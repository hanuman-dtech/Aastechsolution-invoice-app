"""
PDF Service - Invoice PDF generation using ReportLab.

Refactored from invoice.py PDF generation logic.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)

MONEY_QUANT = Decimal("0.01")


class PDFService:
    """Service for generating invoice PDFs."""
    
    @staticmethod
    def to_decimal(value) -> Decimal:
        """Convert value to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    
    @staticmethod
    def money(value) -> str:
        """Format Decimal as money with 2 decimal places."""
        return f"{PDFService.to_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)}"
    
    @staticmethod
    def format_date(value: date) -> str:
        """Format date for display (e.g., 'Feb 28, 2026')."""
        return value.strftime("%b %d, %Y")
    
    def generate_invoice_pdf(
        self,
        filename: str | Path,
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
        payment_terms: str = "Monthly",
        extra_fees: Decimal = Decimal("0.00"),
        extra_fees_label: str = "Other Fees",
    ) -> tuple[Path, Decimal, Decimal, Decimal, Decimal]:
        """
        Generate an invoice PDF.
        
        Returns:
            Tuple of (output_path, labor_subtotal, subtotal, hst_amount, total)
        """
        total_hours = self.to_decimal(total_hours)
        rate_per_hour = self.to_decimal(rate_per_hour)
        hst_rate = self.to_decimal(hst_rate)
        extra_fees = self.to_decimal(extra_fees)
        
        # Calculate amounts
        labor_subtotal = total_hours * rate_per_hour
        subtotal = labor_subtotal + extra_fees
        hst_amount = (subtotal * hst_rate).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        total = subtotal + hst_amount
        
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating PDF: {output_path}")
        
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
        c.drawString(left_margin, header_y, "Client:")
        
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
        c.drawString(left_margin, y, f"Contractor: {contractor_name}")
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
        c.drawRightString(inner_x_value, inner_y, f"{self.money(total_hours)}")
        inner_y -= 6 * mm
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(inner_x_label, inner_y, "Rate / Hour:")
        c.setFont("Helvetica", 10)
        c.drawRightString(inner_x_value, inner_y, f"${self.money(rate_per_hour)}")
        inner_y -= 6 * mm
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(inner_x_label, inner_y, "Labor Fees:")
        c.setFont("Helvetica", 10)
        c.drawRightString(inner_x_value, inner_y, f"${self.money(labor_subtotal)}")
        inner_y -= 6 * mm
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(inner_x_label, inner_y, f"{extra_fees_label}:")
        c.setFont("Helvetica", 10)
        c.drawRightString(inner_x_value, inner_y, f"${self.money(extra_fees)}")
        inner_y -= 6 * mm
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(inner_x_label, inner_y, "Subtotal:")
        c.setFont("Helvetica", 10)
        c.drawRightString(inner_x_value, inner_y, f"${self.money(subtotal)}")
        inner_y -= 6 * mm
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(inner_x_label, inner_y, f"H.S.T. ({int(hst_rate * 100)}%):")
        c.setFont("Helvetica", 10)
        c.drawRightString(inner_x_value, inner_y, f"${self.money(hst_amount)}")
        inner_y -= 8 * mm
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inner_x_label, inner_y, "INVOICE TOTAL:")
        c.drawRightString(inner_x_value, inner_y, f"${self.money(total)}")
        
        # Footer
        y_footer = box_bottom - 15 * mm
        c.setFont("Helvetica", 9)
        c.drawString(left_margin, y_footer, "If you have any questions about this invoice, please contact:")
        y_footer -= 5 * mm
        c.drawString(left_margin, y_footer, f"{vendor_name} | {vendor_email}")
        
        c.showPage()
        c.save()
        
        logger.info(f"Generated PDF at: {output_path.resolve()}")
        
        return output_path, labor_subtotal, subtotal, hst_amount, total
    
    def get_output_directory(self) -> Path:
        """Get the invoice output directory."""
        output_dir = Path(settings.invoice_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir


# Singleton instance
pdf_service = PDFService()
