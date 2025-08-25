from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..db.repo import Repository
from ..config import Settings
from ..keyboards import inline as inline_kb
from ..states.payment_states import AdminPaymentStates
from ..services.i18n_filters import TextKey
from ..services.i18n_filters import TextKey

router = Router()


async def _send_payment_card(chat_id: int, bot, t, repo: Repository, pid: int, has_prev: bool, has_next: bool):
    p = await repo.get_payment(pid)
    if not p:
        return None
    user = await repo.get_user_by_id(p.user_id)
    uname = f"@{user.username}" if user and user.username else "-"
    uid = user.telegram_id if user else "-"
    caption = t("payments_admin_item", pid=p.id, kind=p.kind, amount=p.amount, uname=uname, uid=uid)
    kb = inline_kb.admin_payment_nav_actions_keyboard(t, payment_id=p.id, has_prev=has_prev, has_next=has_next)

    if p.file_type == "photo" and p.file_id:
        return await bot.send_photo(chat_id=chat_id, photo=p.file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
    if p.file_type == "document" and p.file_id:
        return await bot.send_document(chat_id=chat_id, document=p.file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
    return await bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML", reply_markup=kb)


async def _render_current(msg_or_call, state: FSMContext, t, repo: Repository):
    data = await state.get_data()
    ids: list[int] = data.get("pay_ids", [])
    idx: int = data.get("pay_idx", 0)
    if not ids:
        return None
    has_prev = idx > 0
    has_next = idx < len(ids) - 1
    chat_id = msg_or_call.chat.id
    msg = await _send_payment_card(chat_id, msg_or_call.bot, t, repo, ids[idx], has_prev, has_next)
    if msg:
        await state.update_data(view_msg_id=msg.message_id)
    return msg


@router.message(TextKey("btn_admin_payments"))
async def admin_payments_start(message: Message, settings: Settings, repo: Repository, t, state: FSMContext) -> None:
    if message.from_user.id != settings.admin_id:
        return
    pending = await repo.list_pending_payments()
    if not pending:
        await message.answer(t("admin_payments_empty"))
        return
    ids = [p.id for p in pending]
    await state.set_state(AdminPaymentStates.Browsing)
    await state.update_data(pay_ids=ids, pay_idx=0, view_msg_id=None)
    await _render_current(message, state, t, repo)

@router.callback_query(F.data == "paynav:prev", AdminPaymentStates.Browsing)
async def admin_nav_prev(call: CallbackQuery, settings: Settings, repo: Repository, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    data = await state.get_data()
    idx = max(0, (data.get("pay_idx", 0) - 1))
    await state.update_data(pay_idx=idx)
    try:
        await call.message.delete()
    except Exception:
        pass
    await _render_current(call.message, state, t, repo)
    await call.answer()


@router.callback_query(F.data == "paynav:next", AdminPaymentStates.Browsing)
async def admin_nav_next(call: CallbackQuery, settings: Settings, repo: Repository, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    data = await state.get_data()
    ids = data.get("pay_ids", [])
    idx = min(len(ids) - 1, (data.get("pay_idx", 0) + 1))
    await state.update_data(pay_idx=idx)
    try:
        await call.message.delete()
    except Exception:
        pass
    await _render_current(call.message, state, t, repo)
    await call.answer()


@router.callback_query(F.data.startswith("pay:approve:"))
async def admin_approve_any(call: CallbackQuery, settings: Settings, repo: Repository, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return

    pid = int((call.data or "0").split(":")[2])
    p = await repo.get_payment(pid)
    if not p:
        await call.answer("Not found")
        return

    await repo.apply_payment_effect(p)
    await repo.mark_payment_status(pid, status="approved", admin_id=call.from_user.id)

    user = await repo.get_user_by_id(p.user_id)
    if user and user.telegram_id:
        try:
            await call.bot.send_message(user.telegram_id, t("payments_user_done"))
        except Exception:
            pass

    try:
        await call.message.edit_caption(t("payments_admin_approved"), parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(t("payments_admin_approved"), parse_mode="HTML")
        except Exception:
            pass

    data = await state.get_data()
    ids: list[int] = data.get("pay_ids", [])
    if ids:
        idx: int = data.get("pay_idx", 0)
        if pid in ids:
            pos = ids.index(pid)
            ids.pop(pos)
            if idx >= len(ids):
                idx = max(0, len(ids) - 1)
            await state.update_data(pay_ids=ids, pay_idx=idx)
        try:
            await call.message.delete()
        except Exception:
            pass
        if not ids:
            await state.clear()
            await call.message.answer(t("admin_payments_empty"))
        else:
            await _render_current(call.message, state, t, repo)

    await call.answer("OK")


@router.callback_query(F.data.startswith("pay:reject:"))
async def admin_reject_any(call: CallbackQuery, settings: Settings, repo: Repository, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    pid = int((call.data or "0").split(":")[2])
    await state.set_state(AdminPaymentStates.WaitingCancelConfirm)
    await state.update_data(reject_pid=pid)
    await call.message.answer(t("payments_admin_reject_confirm"))
    await call.answer()


@router.message(AdminPaymentStates.WaitingCancelConfirm)
async def admin_reject_confirm(message: Message, settings: Settings, repo: Repository, t, state: FSMContext) -> None:
    if message.from_user.id != settings.admin_id:
        return
    if (message.text or "").strip() != "ПОДТВЕРДИТЬ":
        await message.answer(t("payments_admin_reject_need_caps"))
        return

    data = await state.get_data()
    pid = int(data.get("reject_pid"))
    await repo.mark_payment_status(pid, status="rejected", admin_id=message.from_user.id)

    p = await repo.get_payment(pid)
    if p:
        user = await repo.get_user_by_id(p.user_id)
        if user and user.telegram_id:
            try:
                await message.bot.send_message(user.telegram_id, t("payments_user_rejected"))
            except Exception:
                pass

    ids: list[int] = data.get("pay_ids", [])
    idx: int = data.get("pay_idx", 0)
    view_msg_id = data.get("view_msg_id")

    if pid in ids:
        pos = ids.index(pid)
        ids.pop(pos)
        if idx >= len(ids):
            idx = max(0, len(ids) - 1)

    await state.update_data(pay_ids=ids, pay_idx=idx)
    await state.set_state(AdminPaymentStates.Browsing if ids else None)

    if view_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=view_msg_id)
        except Exception:
            pass

    if not ids:
        await state.clear()
        await message.answer(t("admin_payments_empty"))
    else:
        await _render_current(message, state, t, repo)

@router.callback_query(F.data == "admin:payments")
async def admin_payments_open(call: CallbackQuery, settings: Settings, repo: Repository, t, state: FSMContext) -> None:
    if call.from_user.id != settings.admin_id:
        await call.answer()
        return
    pending = await repo.list_pending_payments()
    if not pending:
        await call.message.edit_text(t("admin_payments_empty"))
        await call.answer()
        return
    ids = [p.id for p in pending]
    await state.set_state(AdminPaymentStates.Browsing)
    await state.update_data(pay_ids=ids, pay_idx=0, view_msg_id=None)
    await _render_current(call.message, state, t, repo)
    await call.answer()
