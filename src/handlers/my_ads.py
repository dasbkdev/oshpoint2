from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from ..db.repo import Repository
from ..keyboards.inline import my_ads_list_kb, my_ad_actions_kb
from .create_ad.preview import _build_caption
from ..services.i18n_filters import TextKey

router = Router()

@router.message(TextKey("btn_my_ads"))
async def my_ads_list(message: Message, repo: Repository, t):
    user = await repo.create_or_get_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    pubs = await repo.list_user_publications(user.id)
    if not pubs:
        await message.answer(t("myads_empty"))
        return

    items: list[tuple[int, str]] = []
    for pub, draft in pubs:
        title = draft.name or draft.short_desc or t("myads_no_title")
        text = title if len(title) <= 40 else title[:37] + "…"
        items.append((pub.id, text))

    await message.answer(t("myads_title"), reply_markup=my_ads_list_kb(items))


@router.callback_query(F.data.startswith("myads:open:"))
async def my_ads_open(call: CallbackQuery, repo: Repository, t):
    await call.answer()
    pub_id = int(call.data.split(":")[2])
    pub = await repo.get_publication(pub_id)
    if not pub:
        await call.message.answer(t("myads_not_found"))
        return

    # найдём соответствующий драфт
    pairs = await repo.list_user_publications(pub.user_id)
    draft = None
    for p, d in pairs:
        if p.id == pub_id:
            draft = d
            break
    if not draft:
        await call.message.answer(t("myads_not_found"))
        return

    caption = await _build_caption(
        draft,
        t,
        seller_username=call.from_user.username,
        seller_id=call.from_user.id,
        bot_username=(await call.bot.get_me()).username,
        sold=bool(pub.is_sold),
    )
    photos = sorted(list(draft.photos), key=lambda p: p.sort_order or 0)

    if photos:
        if len(photos) > 1:
            media = []
            for idx, p in enumerate(photos):
                if idx == 0:
                    media.append(InputMediaPhoto(media=p.file_id, caption=caption, parse_mode="HTML"))
                else:
                    media.append(InputMediaPhoto(media=p.file_id))
            await call.message.answer_media_group(media)
            await call.message.answer(t("myads_actions"), reply_markup=my_ad_actions_kb(pub_id, t))
        else:
            await call.message.answer_photo(
                photos[0].file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=my_ad_actions_kb(pub_id, t),
            )
    else:
        await call.message.answer(caption, parse_mode="HTML", reply_markup=my_ad_actions_kb(pub_id, t))

@router.callback_query(F.data.startswith("myads:sold:"))
async def my_ads_mark_sold(call: CallbackQuery, repo: Repository, t):
    """
    Отмечаем публикацию как ПРОДАНО и стараемся обновить пост в канале.
    В медиа-группе подпись всегда у ПЕРВОГО сообщения — редактируем только его,
    чтобы не ловить ошибку "there is no text in the message to edit".
    """
    await call.answer()
    pub_id = int(call.data.split(":")[2])

    # Ставим флаг в БД
    await repo.set_publish_sold(pub_id, True)

    # Попробуем обновить карточку в канале
    pub = await repo.get_publication(pub_id)
    if pub:
        draft = await repo.get_draft(pub.draft_id)
        if draft and pub.channel_id:
            try:
                caption = await _build_caption(
                    draft,
                    t,
                    seller_username=call.from_user.username,
                    seller_id=call.from_user.id,
                    bot_username=(await call.bot.get_me()).username,
                    sold=True,
                )

                # Если это был альбом — подпись у первого сообщения
                if pub.message_ids_json and len(pub.message_ids_json) > 0:
                    first_id = int(pub.message_ids_json[0])
                    # 1) пробуем как подпись (для фото/альбома)
                    try:
                        await call.bot.edit_message_caption(
                            chat_id=int(pub.channel_id),
                            message_id=first_id,
                            caption=caption,
                            parse_mode="HTML",
                        )
                    except Exception:
                        # 2) если это был текстовый пост — попробуем текст
                        try:
                            await call.bot.edit_message_text(
                                chat_id=int(pub.channel_id),
                                message_id=first_id,
                                text=caption,
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
                else:
                    # На всякий случай обработаем кейс одиночного текстового сообщения
                    try:
                        await call.bot.edit_message_text(
                            chat_id=int(pub.channel_id),
                            message_id=int(pub.id),  # fall-back, почти никогда не нужен
                            text=caption,
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
            except Exception:
                # не мешаем пользователю — просто молча пропустим неудачу
                pass

    await call.message.answer(t("myads_marked_sold"))

@router.callback_query(F.data.startswith("myads:del:"))
async def my_ads_delete(call: CallbackQuery, repo: Repository, t):
    await call.answer()
    pub_id = int(call.data.split(":")[2])

    # сначала удалим посты в канале, если они есть
    pub = await repo.get_publication(pub_id)
    if pub and pub.channel_id and pub.message_ids_json:
        for mid in list(pub.message_ids_json or []):
            try:
                await call.bot.delete_message(chat_id=pub.channel_id, message_id=mid)
            except Exception:
                pass

    await repo.delete_publication(pub_id)
    await call.message.answer(t("myads_deleted"))
