"""
Security utilities - password hashing, JWT tokens, encryption.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def get_password_hash(password: str) -> str:
    """Backward-compatible alias for password hashing."""
    return hash_password(password)


def generate_password(length: int = 16) -> str:
    """Generate a random password."""
    return secrets.token_urlsafe(length)


# JWT Token handling
ALGORITHM = "HS256"


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# Encryption for sensitive data (SMTP passwords, etc.)
def _get_encryption_key() -> bytes:
    """Derive a Fernet key from the secret key."""
    # Use SHA256 to get consistent 32 bytes, then base64 encode for Fernet
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


_fernet = Fernet(_get_encryption_key())


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value for storage."""
    return _fernet.encrypt(plaintext.encode()).decode()


def encrypt_smtp_password(plaintext: str) -> str:
    """Backward-compatible alias for SMTP password encryption."""
    return encrypt_value(plaintext)


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a stored encrypted value."""
    return _fernet.decrypt(ciphertext.encode()).decode()


# Request ID generation
def generate_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return secrets.token_hex(16)


# Invoice number generation
def generate_invoice_number(prefix: str, date: datetime, sequence: int) -> str:
    """Generate a unique invoice number."""
    date_part = date.strftime("%Y%m%d")
    return f"{prefix}-{date_part}-{sequence:03d}"
