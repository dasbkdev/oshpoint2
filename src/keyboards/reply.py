from __future__ import annotations
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_kb(t, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = [
        [KeyboardButton(text=t("btn_create_ad"))],
        [KeyboardButton(text=t("btn_language"))],
        [KeyboardButton(text=t("btn_my_ads"))],
        [KeyboardButton(text=t("btn_payments"))],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=t("btn_admin_payments"))])
    rows.append([KeyboardButton(text=t("btn_settings"))])
    rows.append([KeyboardButton(text=t("btn_profile"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def back_only_kb(t) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("back"))]],
        resize_keyboard=True
    )
