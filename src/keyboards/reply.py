from __future__ import annotations
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_kb(t) -> ReplyKeyboardMarkup:
    # порядок кнопок — по просьбе: язык в конце
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_create_ad"))],
            [KeyboardButton(text=t("btn_my_ads"))],
            [KeyboardButton(text=t("btn_payments"))],
            [KeyboardButton(text=t("btn_profile"))],
            [KeyboardButton(text=t("btn_language"))],
        ],
        resize_keyboard=True
    )

def back_only_kb(t) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("back"))]],
        resize_keyboard=True
    )
