from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...db.repo import Repository
from ...states.ad_creation import AdCreation
from ...keyboards import inline as inline_kb
from .preview import send_preview
from loguru import logger

router = Router()

@router.message(AdCreation.Name)
async def set_name(message: Message, repo: Repository, t, state: FSMContext) -> None:
    draft_id = (await state.get_data()).get("draft_id")
    await repo.update_draft(draft_id, name=(message.text or "").strip())
    await state.set_state(AdCreation.ShortDesc)
    await message.answer(t("ad_ask_short"))

@router.message(AdCreation.ShortDesc)
async def set_short_desc(message: Message, repo: Repository, t, state: FSMContext) -> None:
    draft_id = (await state.get_data()).get("draft_id")
    await repo.update_draft(draft_id, short_desc=(message.text or "").strip())
    await state.set_state(AdCreation.Price)
    await message.answer(t("ad_ask_price"))

@router.message(AdCreation.Price)
async def set_price(message: Message, repo: Repository, t, state: FSMContext) -> None:
    draft_id = (await state.get_data()).get("draft_id")
    raw = (message.text or "").strip()
    try:
        price = int("".join(ch for ch in raw if ch.isdigit()))
    except Exception:
        price = None
    await repo.update_draft(draft_id, price=price)

    draft = await repo.get_draft(draft_id)
    ad_type = (draft.type or "").lower() if draft else ""
    is_search = ad_type in {"buy", "find", "search", "looking"}

    if is_search:
        await state.set_state(AdCreation.City)
        await message.answer(t("ad_choose_city"), reply_markup=inline_kb.city_keyboard(t))
    else:
        await state.set_state(AdCreation.Delivery)
        await message.answer(t("ad_ask_delivery"), reply_markup=inline_kb.delivery_keyboard(t))

@router.callback_query(F.data.startswith("delivery:"), AdCreation.Delivery)
async def choose_delivery(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    opt = call.data.split(":")[1]  # no_ship | country
    draft_id = (await state.get_data()).get("draft_id")
    await repo.update_draft(draft_id, delivery=opt)
    await state.set_state(AdCreation.City)
    await call.message.edit_text(t("ad_choose_city"), reply_markup=inline_kb.city_keyboard(t))

@router.callback_query(F.data.startswith("city:"), AdCreation.City)
async def choose_city(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    city = call.data.split(":")[1]
    draft_id = (await state.get_data()).get("draft_id")
    await repo.update_draft(draft_id, city=city)
    await state.set_state(AdCreation.Photos)
    await call.message.edit_text(t("ad_ask_photos"))

async def _add_photo_and_preview(message: Message, repo: Repository, t, state: FSMContext, file_id: str) -> None:
    data = await state.get_data()
    draft_id = data.get("draft_id")
    if not draft_id:
        await message.answer("Ошибка: черновик не найден.")
        return
    try:
        count = await repo.count_draft_photos(draft_id)
        if count >= 10:
            await message.answer(t("ad_photos_limit"))
            return
        await repo.add_photo_to_draft(draft_id, file_id=file_id, order=count + 1)
        await message.answer(t("ad_photo_added", n=count + 1))

        draft = await repo.get_draft(draft_id)
        await state.set_state(AdCreation.Preview)
        await send_preview(message, draft, t)
    except Exception as e:
        logger.exception("add_photo failed")
        await message.answer(f"Ошибка при сохранении фото: {e}")

@router.message(AdCreation.Photos, F.photo)
async def receive_photo(message: Message, repo: Repository, t, state: FSMContext) -> None:
    await _add_photo_and_preview(message, repo, t, state, message.photo[-1].file_id)

@router.message(AdCreation.Photos, F.document)
async def receive_document_photo(message: Message, repo: Repository, t, state: FSMContext) -> None:
    if message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        await _add_photo_and_preview(message, repo, t, state, message.document.file_id)
        return
    await message.answer(t("ad_ask_photos_only"))

@router.message(AdCreation.Photos)
async def wrong_photo(message: Message, t) -> None:
    await message.answer(t("ad_ask_photos_only"))
