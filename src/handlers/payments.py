from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..db.repo import Repository
from ..keyboards import inline as inline_kb
from ..keyboards import reply as reply_kb
from ..states.payment_states import PaymentStates
from ..services.i18n_filters import TextKey
from ..config import Settings

router = Router()


# Вход строго по ключу перевода (работает с эмодзи и любым текстом из YAML)
@router.message(TextKey("btn_payments"))
async def payments_entry(message: Message, t) -> None:
    await message.answer(t("payments_price"), reply_markup=inline_kb.payments_options_keyboard(t))


@router.callback_query(F.data.in_({"pay:30", "pay:50", "pay:200"}))
async def payments_choose(call: CallbackQuery, repo: Repository, t, state: FSMContext) -> None:
    await call.answer()
    tg_user = call.from_user
    if not tg_user:
        return
    user = await repo.create_or_get_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    amount = int((call.data or "pay:30").split(":")[1])
    kind = "extra" if amount == 30 else ("pin" if amount == 50 else "unlimited")

    payment = await repo.create_payment(user.id, kind=kind, amount=amount)

    await state.set_state(PaymentStates.WaitingReceipt)
    await state.update_data(payment_id=payment.id)

    await call.message.edit_text(
        t("payments_upload_prompt"),
        reply_markup=inline_kb.payments_cancel_keyboard(t),
    )


@router.callback_query(F.data == "pay:cancel", PaymentStates.WaitingReceipt)
async def payments_cancel(call: CallbackQuery, t, state: FSMContext) -> None:
    await call.answer()
    await state.clear()
    await call.message.edit_text(t("payments_cancelled"))
    await call.message.answer(t("back_to_menu"), reply_markup=reply_kb.main_menu_kb(t))


@router.message(PaymentStates.WaitingReceipt)
async def payments_upload(message: Message, repo: Repository, t, state: FSMContext) -> None:
    data = await state.get_data()
    payment_id = data.get("payment_id")
    if not payment_id:
        await state.clear()
        await message.answer(t("payments_cancelled"))
        return

    file_type = None
    file_id = None
    if message.photo:
        file_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.document:
        file_type = "document"
        file_id = message.document.file_id

    if not file_type:
        await message.answer(t("payments_expect_receipt"))
        return

    await repo.attach_payment_receipt(payment_id, file_type=file_type, file_id=file_id)
    await repo.mark_payment_status(payment_id, status="pending")

    # Сообщаем пользователю
    await message.answer(t("payments_user_ok"))

    # Уведомляем админа
    # Берём admin_id из конфигурации напрямую (не через инъекцию)
    admin_id = Settings().admin_id
    p = await repo.get_payment(payment_id)
    user = await repo.get_user_by_id(p.user_id) if p else None
    uname = f"@{user.username}" if user and user.username else "-"
    uid = user.telegram_id if user else "-"
    caption = t("payments_admin_item", pid=p.id, kind=p.kind, amount=p.amount, uname=uname, uid=uid)
    kb = inline_kb.admin_payment_nav_actions_keyboard(t, payment_id=p.id, has_prev=False, has_next=False)

    if file_type == "photo":
        await message.bot.send_photo(chat_id=admin_id, photo=file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
    else:
        await message.bot.send_document(chat_id=admin_id, document=file_id, caption=caption, parse_mode="HTML", reply_markup=kb)

    await state.clear()
