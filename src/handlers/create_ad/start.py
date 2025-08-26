from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...db.repo import Repository
from ...states.ad_creation import AdCreation
from ...keyboards import inline as inline_kb

router = Router()


# Старт создания объявления (кнопка «Создать объявление»)
@router.message(F.text.in_({"Создать объявление", "Жарыя түзүү", "❇️Создать объявление", "❇️Жарыя түзүү"}))
async def start_ad_creation(message: Message, repo: Repository, t, state: FSMContext) -> None:
    user = await repo.create_or_get_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    # Чистим предыдущий незавершённый черновик в состоянии
    await state.clear()
    await state.set_state(AdCreation.Type)
    await message.answer(t("ad_choose_type"), reply_markup=inline_kb.select_ad_type_keyboard(t))


# Выбор типа (Ищу/Продаю/Обмен)
@router.callback_query(F.data.startswith("type:"), AdCreation.Type)
async def choose_type(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    ad_type = call.data.split(":")[1]  # want | sell | trade

    user = await repo.get_user_by_telegram_id(call.from_user.id)
    draft = await repo.get_active_draft(user.id)
    if draft is None:
        draft = await repo.create_draft(user.id, ad_type)
    else:
        await repo.update_draft(draft.id, type=ad_type)

    await state.update_data(draft_id=draft.id)
    await state.set_state(AdCreation.Category)
    await call.message.edit_text(t("ad_choose_category"), reply_markup=inline_kb.select_category_keyboard(t))


# Выбор категории
@router.callback_query(F.data.startswith("cat:"), AdCreation.Category)
async def choose_category(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    category = call.data.split(":")[1]  # bike | parts | accessories | clothes | shoes
    data = await state.get_data()
    draft_id = data.get("draft_id")

    await repo.update_draft(draft_id, category=category, subcategory=None)

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

    # Без подкатегорий — сразу имя
    await state.set_state(AdCreation.Name)
    await call.message.edit_text(t("ad_ask_name"))


# ЕДИНЫЙ обработчик подкатегорий (работает и для bike, и для parts)
@router.callback_query(F.data.regexp(r"^subcat_(bike|parts):(.+)$"), AdCreation.Subcategory)
async def choose_any_subcat(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    m = call.data.split(":", 1)
    # m[0] = "subcat_bike" | "subcat_parts"
    # m[1] = код подкатегории (fix / mtb / wheels / frames ...)

    subcat = m[1]
    data = await state.get_data()
    draft_id = data.get("draft_id")

    # Если по какой-то причине draft_id потерялся — восстановим последнюю DRAFT запись
    if not draft_id:
        user = await repo.get_user_by_telegram_id(call.from_user.id)
        draft = await repo.get_active_draft(user.id)
        if draft is None:
            draft = await repo.create_draft(user.id, ad_type="sell")
        draft_id = draft.id
        await state.update_data(draft_id=draft_id)

    await repo.update_draft(draft_id, subcategory=subcat)

    await state.set_state(AdCreation.Name)
    await call.message.edit_text(t("ad_ask_name"))


# Кнопка «Отмена» в любой момент начала (из выбора типа/категории/подкатегории)
@router.callback_query(F.data == "cancel")
async def cancel_any(call: CallbackQuery, repo: Repository, state: FSMContext, t) -> None:
    await call.answer()
    data = await state.get_data()
    draft_id = data.get("draft_id")
    if draft_id:
        # Полностью удаляем черновик и фото, чтобы «фотки не подтягивались из старого»
        await repo.delete_draft(draft_id, only_if_status_draft=True)
    await state.clear()
    # Нельзя безопасно edit_text, если предыдущее сообщение было с фото — просто отправим новое
    await call.message.answer(t("ad_cancelled"))
