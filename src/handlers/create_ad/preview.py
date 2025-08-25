from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from ...db.repo import Repository
from ...config import Settings
from ...states.ad_creation import AdCreation
from ...keyboards import inline as inline_kb
from ...keyboards import reply as reply_kb
from ...services.telegram_utils import normalize_chat_id

router = Router()


def _seller_url(username: str | None, user_id: int | None) -> str | None:
    if username:
        return f"https://t.me/{username}"
    if user_id:
        return f"tg://user?id={user_id}"
    return None


async def _build_caption(
    draft,
    t,
    *,
    seller_username: str | None = None,
    seller_id: int | None = None,
    bot_username: str | None = None,
) -> str:
    tags = []
    if draft.category == "bike":
        tags.append("#bike")
    elif draft.category == "parts":
        tags.append("#parts")
    elif draft.category == "accessories":
        tags.append("#accessories")
    elif draft.category == "clothes":
        tags.append("#clothes")
    elif draft.category == "shoes":
        tags.append("#shoes")
    if draft.subcategory:
        tags.append(f"#{draft.subcategory}")

    cond = t("cond_new") if draft.condition == "new" else t("cond_used")
    city = t("city_bishkek") if draft.city == "bishkek" else t("city_osh")
    if draft.delivery == "country":
        delivery_line = t("delivery_caption_country")
    elif draft.delivery == "no_ship":
        delivery_line = t("delivery_caption_no_ship")
    else:
        delivery_line = ""

    lines = []
    if tags:
        lines.append(" ".join(tags))
    lines.append(f"{t('cap_line_type_sell')} | {cond} | {city}")
    if draft.name:
        lines.append(f"<b>{draft.name}</b>")
    if draft.short_desc:
        lines.append(f"<i>{draft.short_desc}</i>")
    if draft.detail_desc:
        lines.append(draft.detail_desc)
    if draft.price is not None:
        lines.append(f"{draft.price} KGS")
    if delivery_line:
        lines.append(delivery_line)

    seller = _seller_url(seller_username, seller_id)
    link_lines = []
    if bot_username:
        link_lines.append(f"📣 <a href='https://t.me/{bot_username}'>{t('post_link_post')}</a>")
    if seller:
        link_lines.append(f"😎 <a href='{seller}'>{t('post_link_write_seller')}</a>")
    if link_lines:
        lines.append("")
        lines.extend(link_lines)

    return "\n".join(lines).strip()


async def send_preview(message: Message, draft, t) -> None:
    me = await message.bot.get_me()
    caption = await _build_caption(
        draft,
        t,
        seller_username=message.from_user.username if message.from_user else None,
        seller_id=message.from_user.id if message.from_user else None,
        bot_username=me.username,
    )
    photos = sorted(list(draft.photos), key=lambda p: p.sort_order or 0)
    if photos:
        if len(photos) > 1:
            media = []
            for i, p in enumerate(photos):
                if i == 0:
                    media.append(InputMediaPhoto(media=p.file_id, caption=caption, parse_mode="HTML"))
                else:
                    media.append(InputMediaPhoto(media=p.file_id))
            await message.answer_media_group(media)
            await message.answer(t("preview_controls"), reply_markup=inline_kb.preview_keyboard(t))
        else:
            await message.answer_photo(
                photos[0].file_id, caption=caption, parse_mode="HTML", reply_markup=inline_kb.preview_keyboard(t)
            )
    else:
        await message.answer(caption, parse_mode="HTML", reply_markup=inline_kb.preview_keyboard(t))


@router.callback_query(F.data == "preview:publish", AdCreation.Preview)
async def publish_ad(call: CallbackQuery, repo: Repository, state: FSMContext, settings: Settings, t) -> None:
    await call.answer()
    data = await state.get_data()
    draft_id = data.get("draft_id")
    tg_user = call.from_user
    if not tg_user or not draft_id:
        await call.message.answer("Ошибка публикации.")
        await state.clear()
        return

    user = await repo.create_or_get_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    publication = await repo.publish_draft(draft_id, user.id)
    draft = await repo.get_draft(draft_id)

    me = await call.bot.get_me()
    caption = await _build_caption(
        draft,
        t,
        seller_username=user.username,
        seller_id=user.telegram_id,
        bot_username=me.username,
    )

    photos = sorted(list(draft.photos), key=lambda p: p.sort_order or 0)
    chat_target = normalize_chat_id(settings.bike_channel)
    topic_id = settings.bike_topic_id
    if not chat_target:
        await call.message.answer(t("publish_channel_not_set"))
        await state.clear()
        return

    bot = call.bot
    sent_message_ids: list[int] = []
    channel_chat_id: int | None = None
    kwargs = {"message_thread_id": topic_id} if topic_id is not None else {}

    try:
        if photos:
            if len(photos) > 1:
                media = []
                for idx, p in enumerate(photos):
                    if idx == 0:
                        media.append(InputMediaPhoto(media=p.file_id, caption=caption, parse_mode="HTML"))
                    else:
                        media.append(InputMediaPhoto(media=p.file_id))
                msgs = await bot.send_media_group(chat_id=chat_target, media=media, **kwargs)
                sent_message_ids = [m.message_id for m in msgs]
                channel_chat_id = msgs[0].chat.id if msgs else None
            else:
                m = await bot.send_photo(
                    chat_id=chat_target, photo=photos[0].file_id, caption=caption, parse_mode="HTML", **kwargs
                )
                sent_message_ids = [m.message_id]
                channel_chat_id = m.chat.id
        else:
            m = await bot.send_message(chat_id=chat_target, text=caption, parse_mode="HTML", **kwargs)
            sent_message_ids = [m.message_id]
            channel_chat_id = m.chat.id
    except TelegramForbiddenError:
        await call.message.answer(t("publish_no_rights"))
    except TelegramBadRequest as e:
        await call.message.answer(t("publish_bad_request", error=str(e)))
    except Exception as e:
        await call.message.answer(t("publish_unknown_error", error=str(e)))

    if channel_chat_id and sent_message_ids:
        await repo.attach_publication_messages(
            publication.id, channel_id=channel_chat_id, message_ids=sent_message_ids
        )

    await state.clear()
    # ❗️здесь была ошибка: main_menu -> main_menu_kb
    await call.message.answer(t("published_ok"), reply_markup=reply_kb.main_menu_kb(t))


@router.callback_query(F.data == "preview:cancel", AdCreation.Preview)
async def cancel_ad(call: CallbackQuery, repo: Repository, state: FSMContext, t) -> None:
    """Полная отмена: удаляем черновик и все фото, чтобы ничего не «подтянулось» в следующий раз."""
    await call.answer()
    data = await state.get_data()
    draft_id = data.get("draft_id")
    if draft_id:
        await repo.delete_draft(draft_id, only_if_status_draft=True)
    await state.clear()
    await call.message.edit_text(t("ad_cancelled"))
