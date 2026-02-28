"""
Email Service - SMTP email sending for invoices.

Refactored from invoice.py email logic.
"""

import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decrypt_value
from app.models import EmailLog, EmailStatus, Invoice, SmtpConfig


logger = get_logger(__name__)


class EmailService:
    """Service for sending invoice emails via SMTP."""

    @staticmethod
    def build_invoice_email_template(
        *,
        client_name: str,
        contractor_name: str,
        start_date: str,
        end_date: str,
        invoice_number: str,
    ) -> tuple[str, str]:
        """
        Build formatted invoice email subject/body for SMTP/SendGrid/SES.

        Dynamic variables:
        - clientName
        - contractorName
        - startDate
        - endDate
        """
        subject = (
            f"Invoice {invoice_number} | {contractor_name} | {start_date} - {end_date}"
        )
        body = (
            f"Hi {client_name},\n\n"
            f"Please find attached the invoice for {contractor_name} "
            f"for the period {start_date} – {end_date}.\n\n"
            "Kindly confirm receipt and let me know if anything further is required.\n\n"
            "Thank you,\n\n"
            "Sai Ram Thati\n"
            "Founder & Principal DevOps Engineer\n"
            "AAS Tech Solutions Corp\n"
            "Cloud Engineering | DevOps & SRE | AI Infrastructure | Platform Modernization\n"
            "Toronto, ON, Canada\n"
            "sairam_thati@aastechsolutions.com\n"
            "www.aastechsolutions.com\n"
            "linkedin.com/in/sairamthati"
        )
        return subject, body
    
    async def get_smtp_config(
        self,
        db: AsyncSession,
        vendor_id: Optional[str] = None,
    ) -> Optional[SmtpConfig]:
        """
        Get SMTP configuration.
        
        First tries vendor-specific config, then falls back to global.
        """
        # Try vendor-specific first
        if vendor_id:
            result = await db.execute(
                select(SmtpConfig)
                .where(SmtpConfig.vendor_id == vendor_id)
                .where(SmtpConfig.is_active == True)
            )
            config = result.scalar_one_or_none()
            if config:
                return config
        
        # Fall back to global (vendor_id is NULL)
        result = await db.execute(
            select(SmtpConfig)
            .where(SmtpConfig.vendor_id.is_(None))
            .where(SmtpConfig.is_active == True)
        )
        return result.scalar_one_or_none()
    
    def send_email(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        smtp_from: str,
        recipient_email: str,
        subject: str,
        body: str,
        attachment_path: Optional[Path] = None,
        use_tls: bool = True,
    ) -> None:
        """
        Send an email via SMTP.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password (decrypted)
            smtp_from: From email address
            recipient_email: Recipient email address
            subject: Email subject
            body: Email body text
            attachment_path: Optional path to PDF attachment
            use_tls: Whether to use STARTTLS
        """
        msg = EmailMessage()
        msg["From"] = smtp_from
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.set_content(body)
        
        # Add PDF attachment if provided
        if attachment_path and attachment_path.exists():
            pdf_bytes = attachment_path.read_bytes()
            msg.add_attachment(
                pdf_bytes,
                maintype="application",
                subtype="pdf",
                filename=attachment_path.name,
            )
        
        logger.info(f"Sending email to {recipient_email} via {smtp_host}:{smtp_port}")
        
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            if use_tls:
                server.starttls()
            
            if smtp_user:
                if not smtp_password:
                    raise RuntimeError(
                        "SMTP password is empty. Configure SMTP credentials."
                    )
                try:
                    server.login(smtp_user, smtp_password)
                except smtplib.SMTPAuthenticationError as exc:
                    raise RuntimeError(
                        "SMTP authentication failed (535). Check SMTP_USER / SMTP_PASSWORD. "
                        "For iCloud custom domain, use smtp.mail.me.com:587 with an Apple app-specific password."
                    ) from exc
            
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {recipient_email}")
    
    async def send_invoice_email(
        self,
        db: AsyncSession,
        invoice: Invoice,
        attachment_path: Path,
        smtp_config: Optional[SmtpConfig] = None,
    ) -> EmailLog:
        """
        Send an invoice email and create log entry.
        
        Args:
            db: Database session
            invoice: Invoice to send
            attachment_path: Path to the PDF file
            smtp_config: Optional SMTP config (will fetch from DB if not provided)
            
        Returns:
            EmailLog record
        """
        # Get customer info
        customer = invoice.customer
        vendor = customer.vendor
        
        # Get SMTP config
        if not smtp_config:
            smtp_config = await self.get_smtp_config(db, vendor.id)
        
        if not smtp_config:
            # Fall back to environment variables
            smtp_host = settings.smtp_host
            smtp_port = settings.smtp_port
            smtp_user = settings.smtp_user
            smtp_password = settings.smtp_password
            smtp_from = settings.smtp_from or vendor.email
            use_tls = settings.smtp_use_tls
        else:
            smtp_host = smtp_config.host
            smtp_port = smtp_config.port
            smtp_user = smtp_config.username
            smtp_password = decrypt_value(smtp_config.encrypted_password)
            smtp_from = smtp_config.from_email
            use_tls = smtp_config.use_tls
        
        # Resolve dynamic names separately.
        # clientName   -> customer.name (recipient/client)
        # contractorName -> customer.contractor_name (or vendor.default_contractor fallback)
        client_name = (customer.name or "").strip()
        contractor_name = (customer.contractor_name or "").strip()

        # If data entry made them identical, prefer vendor default contractor when available.
        if contractor_name.lower() == client_name.lower() and getattr(vendor, "default_contractor", None):
            contractor_name = vendor.default_contractor.strip()

        if not contractor_name:
            contractor_name = "Contractor"

        # Build email content using dynamic template
        subject, body = self.build_invoice_email_template(
            client_name=client_name,
            contractor_name=contractor_name,
            start_date=invoice.period_start.strftime("%b %d, %Y"),
            end_date=invoice.period_end.strftime("%b %d, %Y"),
            invoice_number=invoice.invoice_number,
        )
        
        # Create email log
        email_log = EmailLog(
            invoice_id=invoice.id,
            recipient_email=customer.email,
            subject=subject,
            status=EmailStatus.PENDING,
        )
        db.add(email_log)
        await db.flush()
        
        try:
            # Send email
            self.send_email(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                smtp_from=smtp_from,
                recipient_email=customer.email,
                subject=subject,
                body=body,
                attachment_path=attachment_path,
                use_tls=use_tls,
            )
            
            # Update log
            email_log.status = EmailStatus.SENT
            email_log.sent_at = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            email_log.status = EmailStatus.FAILED
            email_log.error_message = str(e)
            email_log.retry_count += 1
            raise
        
        await db.commit()
        return email_log
    
    async def test_smtp_connection(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        test_email: str,
        use_tls: bool = True,
    ) -> tuple[bool, str]:
        """
        Test SMTP connection and send a test email.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                if use_tls:
                    server.starttls()
                
                if smtp_user:
                    server.login(smtp_user, smtp_password)
                
                # Send test email
                msg = EmailMessage()
                msg["From"] = smtp_user
                msg["To"] = test_email
                msg["Subject"] = "Invoice Enterprise Console - SMTP Test"
                msg.set_content(
                    "This is a test email from Invoice Enterprise Console.\n\n"
                    "If you received this, your SMTP configuration is working correctly."
                )
                server.send_message(msg)
            
            return True, "SMTP connection successful. Test email sent."
        
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed. Check username and password."
        except smtplib.SMTPConnectError:
            return False, f"Could not connect to {smtp_host}:{smtp_port}"
        except TimeoutError:
            return False, f"Connection to {smtp_host}:{smtp_port} timed out"
        except Exception as e:
            return False, f"SMTP error: {str(e)}"


# Singleton instance
email_service = EmailService()
