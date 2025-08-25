from __future__ import annotations
from aiogram import Router
from . import start, form_fields, preview

router = Router()
router.include_router(start.router)
router.include_router(form_fields.router)
router.include_router(preview.router)

__all__ = ["router"]
