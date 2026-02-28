"""
Schedule Service - Billing period computation and schedule matching.

Refactored from invoice.py schedule logic.
"""

from datetime import date, timedelta

from app.models import BillingFrequency, Contract, ScheduleConfig
from app.core.logging import get_logger


logger = get_logger(__name__)


class ScheduleService:
    """Service for schedule-related computations."""
    
    @staticmethod
    def compute_billing_period(run_date: date, frequency: BillingFrequency) -> tuple[date, date]:
        """
        Compute (period_start, period_end) for the invoice to generate on run_date.
        
        Args:
            run_date: The date the invoice is being generated
            frequency: Billing frequency (weekly, biweekly, monthly)
            
        Returns:
            Tuple of (period_start, period_end) dates
        """
        period_end = run_date - timedelta(days=1)
        
        if frequency == BillingFrequency.WEEKLY:
            period_start = period_end - timedelta(days=6)
        elif frequency == BillingFrequency.BIWEEKLY:
            period_start = period_end - timedelta(days=13)
        elif frequency == BillingFrequency.MONTHLY:
            first_of_current_month = run_date.replace(day=1)
            period_end = first_of_current_month - timedelta(days=1)
            period_start = period_end.replace(day=1)
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")
        
        logger.debug(
            f"Computed billing period for {frequency.value}: "
            f"{period_start.isoformat()} to {period_end.isoformat()}"
        )
        
        return period_start, period_end
    
    @staticmethod
    def should_invoice_today(
        run_date: date,
        frequency: BillingFrequency,
        schedule: ScheduleConfig,
    ) -> bool:
        """
        Determine whether an invoice should be generated for a customer on run_date.
        
        Args:
            run_date: The date to check
            frequency: Billing frequency
            schedule: Schedule configuration with weekday/day settings
            
        Returns:
            True if invoice should be generated today
        """
        if not schedule.is_enabled:
            logger.debug(f"Schedule disabled for customer {schedule.customer_id}")
            return False
        
        if frequency == BillingFrequency.WEEKLY:
            result = run_date.weekday() == schedule.billing_weekday
            logger.debug(
                f"Weekly check: run_date weekday={run_date.weekday()}, "
                f"billing_weekday={schedule.billing_weekday}, match={result}"
            )
            return result
        
        if frequency == BillingFrequency.BIWEEKLY:
            if run_date.weekday() != schedule.billing_weekday:
                return False
            days_since_anchor = (run_date - schedule.anchor_date).days
            result = days_since_anchor % 14 == 0
            logger.debug(
                f"Biweekly check: days_since_anchor={days_since_anchor}, match={result}"
            )
            return result
        
        if frequency == BillingFrequency.MONTHLY:
            result = run_date.day == schedule.billing_day
            logger.debug(
                f"Monthly check: run_date day={run_date.day}, "
                f"billing_day={schedule.billing_day}, match={result}"
            )
            return result
        
        raise ValueError(f"Unsupported frequency: {frequency}")
    
    @staticmethod
    def compute_next_invoice_date(
        from_date: date,
        frequency: BillingFrequency,
        schedule: ScheduleConfig,
    ) -> date:
        """
        Compute the next invoice generation date from a given date.
        
        Args:
            from_date: Starting date
            frequency: Billing frequency
            schedule: Schedule configuration
            
        Returns:
            Next invoice date
        """
        check_date = from_date
        
        # Search up to 60 days ahead
        for _ in range(60):
            if ScheduleService.should_invoice_today(check_date, frequency, schedule):
                return check_date
            check_date += timedelta(days=1)
        
        # Fallback: estimate based on frequency
        if frequency == BillingFrequency.WEEKLY:
            days_until_billing = (schedule.billing_weekday - from_date.weekday()) % 7
            if days_until_billing == 0:
                days_until_billing = 7
            return from_date + timedelta(days=days_until_billing)
        
        if frequency == BillingFrequency.BIWEEKLY:
            days_until_billing = (schedule.billing_weekday - from_date.weekday()) % 7
            if days_until_billing == 0:
                days_until_billing = 7
            next_date = from_date + timedelta(days=days_until_billing)
            days_since_anchor = (next_date - schedule.anchor_date).days
            if days_since_anchor % 14 != 0:
                next_date += timedelta(days=7)
            return next_date
        
        if frequency == BillingFrequency.MONTHLY:
            # Find the billing_day in current or next month
            current_day = from_date.day
            if current_day < schedule.billing_day:
                # This month
                try:
                    return from_date.replace(day=schedule.billing_day)
                except ValueError:
                    # billing_day doesn't exist in this month
                    pass
            
            # Next month
            if from_date.month == 12:
                next_month = from_date.replace(year=from_date.year + 1, month=1, day=1)
            else:
                next_month = from_date.replace(month=from_date.month + 1, day=1)
            
            try:
                return next_month.replace(day=schedule.billing_day)
            except ValueError:
                # billing_day doesn't exist, use last day of month
                if next_month.month == 12:
                    end_of_month = next_month.replace(year=next_month.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_of_month = next_month.replace(month=next_month.month + 1, day=1) - timedelta(days=1)
                return end_of_month
        
        raise ValueError(f"Unsupported frequency: {frequency}")
    
    @staticmethod
    def format_date(value: date) -> str:
        """Format date for display (e.g., 'Feb 28, 2026')."""
        return value.strftime("%b %d, %Y")
    
    @staticmethod
    def weekday_name(weekday: int) -> str:
        """Get weekday name from number (0=Monday)."""
        names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return names[weekday]


# Singleton instance
schedule_service = ScheduleService()
