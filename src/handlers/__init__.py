from __future__ import annotations
from .admin_utils import router as admin_utils_router
from .common import router as common_router
from .create_ad import router as create_ad_router
from .admin import router as admin_router
from .payments import router as payments_router
from .admin_payments import router as admin_payments_router
from .my_ads import router as my_ads_router

__all__ = [
    "common_router",
    "create_ad_router",
    "admin_router",
    "payments_router",
    "admin_payments_router",
    "my_ads_router",
    "admin_utils_router",
]
