from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...db.repo import Repository
from ...states.ad_creation import AdCreation
from ...keyboards import inline as inline_kb
from ...keyboards import reply as reply_kb
from ...services.i18n_filters import TextKey

router = Router()


# запуск мастера создания объявления — теперь по ключу из i18n
@router.message(TextKey("btn_create_ad"))
async def start_ad_creation(message: Message, repo: Repository, t, state: FSMContext) -> None:
    user = await repo.create_or_get_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    # проверка лимита перед стартом мастера
    can, secs = await repo.get_publish_availability(user.id)
    if not can:
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        when = f"{h:02d}:{m:02d}:{s:02d}"
        msg = t("limit_exceeded", when=when)
        if msg == "limit_exceeded":
            msg = f"Лимит публикаций — 1 раз в 7 дней. Следующая публикация через: {when}"
        await message.answer(msg)
        return

    await state.set_state(AdCreation.Type)
    await message.answer(t("ad_choose_type"), reply_markup=inline_kb.select_ad_type_keyboard(t))


@router.callback_query(F.data.startswith("type:"), AdCreation.Type)
async def choose_type(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    ad_type = call.data.split(":")[1]
    user = await repo.get_user_by_telegram_id(call.from_user.id)
    draft = await repo.get_active_draft(user.id)
    if draft is None:
        draft = await repo.create_draft(user.id, ad_type)
    else:
        await repo.update_draft(draft.id, type=ad_type)
    await state.update_data(draft_id=draft.id)

    await state.set_state(AdCreation.Category)
    await call.message.edit_text(t("ad_choose_category"), reply_markup=inline_kb.select_category_keyboard(t))


@router.callback_query(F.data.startswith("cat:"), AdCreation.Category)
async def choose_category(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    category = call.data.split(":")[1]
    data = await state.get_data()
    draft_id = data.get("draft_id")
    await repo.update_draft(draft_id, category=category, subcategory=None)

    # Велосипеды и Компоненты имеют подкатегории
    if category == "bike":
        await state.set_state(AdCreation.Subcategory)
        await call.message.edit_text(
            t("ad_choose_subcategory_bike"), reply_markup=inline_kb.select_bike_subcategory_keyboard(t)
        )
        return
    if category == "parts":
        await state.set_state(AdCreation.Subcategory)
        await call.message.edit_text(
            t("ad_choose_subcategory_parts"), reply_markup=inline_kb.select_parts_subcategory_keyboard(t)
        )
        return

    # Остальные — сразу к имени
    await state.set_state(AdCreation.Name)
    await call.message.edit_text(t("ad_ask_name"))


@router.callback_query(F.data.startswith("subcat_bike:"), AdCreation.Subcategory)
async def choose_bike_subcat(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    subcat = call.data.split(":")[1]
    draft_id = (await state.get_data()).get("draft_id")
    await repo.update_draft(draft_id, subcategory=subcat)

    await state.set_state(AdCreation.Name)
    await call.message.edit_text(t("ad_ask_name"))


@router.callback_query(F.data.startswith("subcat_parts:"), AdCreation.Subcategory)
async def choose_parts_subcat(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    subcat = call.data.split(":")[1]
    draft_id = (await state.get_data()).get("draft_id")
    await repo.update_draft(draft_id, subcategory=subcat)

    await state.set_state(AdCreation.Name)
    await call.message.edit_text(t("ad_ask_name"))
