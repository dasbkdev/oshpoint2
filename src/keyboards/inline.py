from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---- Категории ----
def select_ad_type_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("ad_type_want"), callback_data="type:want"),
            InlineKeyboardButton(text=t("ad_type_sell"), callback_data="type:sell"),
            InlineKeyboardButton(text=t("ad_type_trade"), callback_data="type:trade"),
        ],
        [InlineKeyboardButton(text=t("cancel"), callback_data="cancel")],
    ])

def select_category_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("ad_cat_bike"), callback_data="cat:bike"),
            InlineKeyboardButton(text=t("ad_cat_parts"), callback_data="cat:parts"),
        ],
        [
            InlineKeyboardButton(text=t("ad_cat_accessories"), callback_data="cat:accessories"),
            InlineKeyboardButton(text=t("ad_cat_clothes"), callback_data="cat:clothes"),
        ],
        [InlineKeyboardButton(text=t("ad_cat_shoes"), callback_data="cat:shoes")],  # Новое: Обувь
    ])

# ---- Подкатегории: Велосипеды ----
def select_bike_subcategory_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("ad_subcat_fix"), callback_data="subcat_bike:fix"),
            InlineKeyboardButton(text=t("ad_subcat_mtb"), callback_data="subcat_bike:mtb"),
        ],
        [
            InlineKeyboardButton(text=t("ad_subcat_kids"), callback_data="subcat_bike:kids"),
            InlineKeyboardButton(text=t("ad_subcat_road"), callback_data="subcat_bike:road"),
        ],
        [
            InlineKeyboardButton(text=t("ad_subcat_gravel"), callback_data="subcat_bike:gravel"),
            InlineKeyboardButton(text=t("ad_subcat_city"), callback_data="subcat_bike:city"),
        ],
        [InlineKeyboardButton(text=t("ad_subcat_other"), callback_data="subcat_bike:other")],
    ])

# ---- Подкатегории: Компоненты ----
def select_parts_subcategory_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("comp_subcat_frames"), callback_data="subcat_parts:frames"),
            InlineKeyboardButton(text=t("comp_subcat_forks"), callback_data="subcat_parts:forks"),
        ],
        [
            InlineKeyboardButton(text=t("comp_subcat_brakes"), callback_data="subcat_parts:brakes"),
            InlineKeyboardButton(text=t("comp_subcat_wheels"), callback_data="subcat_parts:wheels"),
        ],
        [
            InlineKeyboardButton(text=t("comp_subcat_bars"), callback_data="subcat_parts:bars"),
            InlineKeyboardButton(text=t("comp_subcat_crankset"), callback_data="subcat_parts:crankset"),
        ],
        [
            InlineKeyboardButton(text=t("comp_subcat_saddle"), callback_data="subcat_parts:saddle"),
            InlineKeyboardButton(text=t("comp_subcat_other"), callback_data="subcat_parts:other"),
        ],
    ])

# ---- Остальные клавиатуры ----
def condition_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("cond_new"), callback_data="cond:new"),
            InlineKeyboardButton(text=t("cond_used"), callback_data="cond:used"),
        ],
        [InlineKeyboardButton(text=t("back"), callback_data="back_short")],
    ])

def city_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("city_bishkek"), callback_data="city:bishkek"),
            InlineKeyboardButton(text=t("city_osh"), callback_data="city:osh"),
        ],
    ])

def delivery_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("delivery_no_ship"), callback_data="delivery:no_ship"),
            InlineKeyboardButton(text=t("delivery_country"), callback_data="delivery:country"),
        ]
    ])

def preview_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("publish"), callback_data="preview:publish"),
            InlineKeyboardButton(text=t("cancel"), callback_data="preview:cancel"),
        ],
    ])

# ---- Платежи / Админ (оставил как были) ----
def payments_options_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("pay_30_btn"), callback_data="pay:30"),
            InlineKeyboardButton(text=t("pay_50_btn"), callback_data="pay:50"),
            InlineKeyboardButton(text=t("pay_200_btn"), callback_data="pay:200"),
        ]
    ])

def payments_cancel_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("cancel"), callback_data="pay:cancel")]
    ])

def admin_payment_nav_actions_keyboard(t, payment_id: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    rows = []
    nav_row = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="««", callback_data="paynav:prev"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="»»", callback_data="paynav:next"))
    if nav_row:
        rows.append(nav_row)
    rows.append([
        InlineKeyboardButton(text=t("admin_limit_btn"), callback_data=f"pay:approve:{payment_id}"),
        InlineKeyboardButton(text=t("admin_reject_btn"), callback_data=f"pay:reject:{payment_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def my_ad_actions(t, publish_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("ad_mark_sold_btn"), callback_data=f"ads:sold:{publish_id}"),
        InlineKeyboardButton(text=t("ad_delete_btn"), callback_data=f"ads:delete:{publish_id}"),
    ]])

def my_ads_list_kb(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """
    items: список пар (publish_id, title)
    Строит вертикальный список inline-кнопок «Мои объявления».
    """
    rows: list[list[InlineKeyboardButton]] = []
    for pub_id, title in items:
        rows.append([InlineKeyboardButton(text=title, callback_data=f"myads:open:{pub_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def my_ad_actions_kb(pub_id: int, t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_sold"), callback_data=f"myads:sold:{pub_id}"),
            InlineKeyboardButton(text=t("btn_delete"), callback_data=f"myads:del:{pub_id}"),
        ]
    ])

