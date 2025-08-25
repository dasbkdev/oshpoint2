from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from ..db.repo import Repository
from ..config import Settings
from ..states.admin_states import AdminStates

router = Router()

# вход из common: callback admin:users / admin:rules

@router.callback_query(F.data == "admin:users")
async def admin_users_entry(call: CallbackQuery, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    await state.set_state(AdminStates.WaitingUserLookup)
    await call.message.edit_text(t("admin_users_prompt"))

@router.message(AdminStates.WaitingUserLookup)
async def admin_user_lookup(message: Message, repo: Repository, settings: Settings, t, state: FSMContext) -> None:
    if message.from_user.id != settings.admin_id:
        return
    query = (message.text or "").strip()
    user = None
    if query.isdigit():
        user = await repo.get_user_by_telegram_id(int(query))
    if not user:
        user = await repo.get_user_by_username(query)
    if not user:
        await message.answer(t("admin_user_not_found"))
        return

    await state.update_data(target_user_id=user.id)

    # показать профиль пользователя
    total = await repo.count_user_published_total(user.id)
    uname = f"@{user.username}" if user.username else str(user.telegram_id)
    lang_readable = "Русский" if (user.lang or "ru") == "ru" else "Кыргызча"

    lines = [
        f"👤 <b>{t('profile_title')}</b>",
        f"Username: {uname}",
        f"{t('profile_lang')}: {lang_readable}",
        f"{t('profile_total')}: {total}",
    ]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("admin_edit_lang_btn"), callback_data="admin:edit_lang"),
                InlineKeyboardButton(text=t("admin_limit_btn"), callback_data="admin:limit"),
            ],
            [InlineKeyboardButton(text=t("back"), callback_data="admin:back_main")],
        ]
    )
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "admin:back_main")
async def admin_back_main(call: CallbackQuery, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    await state.clear()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("admin_users_btn"), callback_data="admin:users")],
            [InlineKeyboardButton(text=t("admin_rules_btn"), callback_data="admin:rules")],
        ]
    )
    await call.message.edit_text(t("settings_stub"), reply_markup=kb)

# --- Изменить язык пользователя ---

@router.callback_query(F.data == "admin:edit_lang")
async def admin_edit_lang(call: CallbackQuery, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=t("lang_ru"), callback_data="admin:set_lang:ru"),
            InlineKeyboardButton(text=t("lang_ky"), callback_data="admin:set_lang:ky"),
        ]]
    )
    await call.message.answer(t("admin_choose_lang"), reply_markup=kb)

@router.callback_query(F.data.startswith("admin:set_lang:"))
async def admin_set_lang(call: CallbackQuery, repo: Repository, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    data = await state.get_data()
    user_id = data.get("target_user_id")
    if not user_id:
        await call.answer()
        return
    lang = (call.data or "").split(":", 2)[2]
    await repo.set_user_lang(user_id, lang)
    await call.answer("OK")
    await call.message.answer(t("admin_lang_updated"))

# --- Лимиты ---

@router.callback_query(F.data == "admin:limit")
async def admin_limit_menu(call: CallbackQuery, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("admin_limit_unlimited"), callback_data="admin:limit_unlimited")],
            [InlineKeyboardButton(text=t("admin_limit_quota"), callback_data="admin:limit_quota")],
            [InlineKeyboardButton(text=t("admin_limit_reset"), callback_data="admin:limit_reset")],
        ]
    )
    await call.message.answer(t("admin_limit_prompt"), reply_markup=kb)

@router.callback_query(F.data == "admin:limit_unlimited")
async def admin_limit_unlimited(call: CallbackQuery, repo: Repository, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    data = await state.get_data()
    user_id = data.get("target_user_id")
    if not user_id:
        await call.answer()
        return
    await repo.set_unlimited_month(user_id)
    await call.answer("OK")
    await call.message.answer(t("admin_limit_set_unlimited"))

@router.callback_query(F.data == "admin:limit_quota")
async def admin_limit_quota(call: CallbackQuery, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    await state.set_state(AdminStates.WaitingQuotaNumber)
    await call.message.answer(t("admin_limit_quota_ask"))

@router.message(AdminStates.WaitingQuotaNumber)
async def admin_limit_quota_number(message: Message, repo: Repository, settings: Settings, t, state: FSMContext) -> None:
    if message.from_user.id != settings.admin_id:
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(t("admin_limit_quota_invalid"))
        return
    total = int(raw)
    data = await state.get_data()
    user_id = data.get("target_user_id")
    if not user_id:
        await message.answer("No target user.")
        await state.clear()
        return
    await repo.set_quota_month(user_id, total)
    await state.set_state(None)
    await message.answer(t("admin_limit_set_quota", n=total))

@router.callback_query(F.data == "admin:limit_reset")
async def admin_limit_reset(call: CallbackQuery, repo: Repository, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    data = await state.get_data()
    user_id = data.get("target_user_id")
    if not user_id:
        await call.answer()
        return
    await repo.reset_limit_to_default(user_id)
    await call.answer("OK")
    await call.message.answer(t("admin_limit_reset_ok"))

# --- Изменить правила ---

@router.callback_query(F.data == "admin:rules")
async def admin_rules_start(call: CallbackQuery, settings: Settings, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    await state.set_state(AdminStates.WaitingRulesText)
    await call.message.edit_text(t("admin_rules_prompt"))

@router.message(AdminStates.WaitingRulesText)
async def admin_rules_set(message: Message, repo: Repository, settings: Settings, t, state: FSMContext) -> None:
    if message.from_user.id != settings.admin_id:
        return
    text = message.html_text or message.text or ""
    await repo.set_rules(text)
    await state.clear()
    await message.answer(t("admin_rules_updated"))
