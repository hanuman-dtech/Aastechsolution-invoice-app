"""
Structured logging configuration with request ID tracking.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any

from app.core.config import settings


# Context variable for request ID tracking
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Add request_id to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "N/A"
        return True


class StructuredFormatter(logging.Formatter):
    """JSON-like structured formatter for production."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "N/A"),
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Simple structured format (can be switched to JSON in production)
        return f"[{log_data['timestamp']}] [{log_data['level']}] [{log_data['request_id']}] {log_data['logger']}: {log_data['message']}"


class DevelopmentFormatter(logging.Formatter):
    """Colored formatter for development."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        request_id = getattr(record, "request_id", "N/A")
        
        message = f"{color}[{record.levelname}]{self.RESET} [{request_id[:8]}] {record.name}: {record.getMessage()}"
        
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


def setup_logging() -> None:
    """Configure application logging."""
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.addFilter(RequestIdFilter())
    
    if settings.environment == "development":
        console_handler.setFormatter(DevelopmentFormatter())
    else:
        console_handler.setFormatter(StructuredFormatter())
    
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.debug else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


# Application logger
logger = get_logger("invoice_enterprise")
