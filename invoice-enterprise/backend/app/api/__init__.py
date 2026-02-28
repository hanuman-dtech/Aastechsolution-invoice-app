"""
API routes initialization.
"""

from fastapi import APIRouter

from app.api.routes import customers, dashboard, invoices, logs, smtp, vendors


# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(dashboard.router)
api_router.include_router(invoices.router)
api_router.include_router(customers.router)
api_router.include_router(vendors.router)
api_router.include_router(smtp.router)
api_router.include_router(logs.router)
