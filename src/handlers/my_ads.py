from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

from ..db.repo import Repository
from ..keyboards.inline import my_ads_list_kb, my_ad_actions_kb
from .create_ad.preview import _build_caption

router = Router()

USER_MY_ADS_BUTTONS = {"📖Мои Объявления", "📖Менин жарыяларым"}


@router.message(F.text.in_(USER_MY_ADS_BUTTONS))
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


async def _edit_channel_post_safely(bot, chat_id: int, message_id: int, new_caption_html: str) -> bool:
    """
    Обновляем пост в канале.
    Сначала пробуем caption (фото/медиа), если сервер ругнётся — пробуем text.
    """
    try:
        await bot.edit_message_caption(chat_id=chat_id, message_id=message_id,
                                       caption=new_caption_html, parse_mode="HTML")
        return True
    except TelegramBadRequest as e:
        if "no caption" in str(e).lower() or "no text in the message to edit" in str(e).lower():
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                            text=new_caption_html, parse_mode="HTML")
                return True
            except Exception:
                return False
        return False
    except Exception:
        return False


async def _edit_reply_msg_safely(message_obj: Message, new_text: str) -> None:
    """
    Обновляем сообщение, под которым нажали кнопку:
    - если это фото/медиа — правим caption,
    - если текст — правим text,
    - если ничего не получилось — шлём новый ответ.
    """
    try:
        # чаще всего это текстовый "меню"-месседж
        await message_obj.edit_text(new_text, parse_mode="HTML")
        return
    except TelegramBadRequest as e:
        if "no text in the message to edit" in str(e).lower():
            # значит это было фото/медиасообщение с caption
            try:
                await message_obj.edit_caption(new_text, parse_mode="HTML")
                return
            except Exception:
                pass
    except Exception:
        pass

    # Фолбэк — просто новое сообщение
    try:
        await message_obj.answer(new_text)
    except Exception:
        pass


@router.callback_query(F.data.startswith("myads:sold:"))
async def my_ads_mark_sold(call: CallbackQuery, repo: Repository, t):
    await call.answer()
    pub_id = int(call.data.split(":")[2])

    # 1) ставим флаг в БД
    await repo.set_publish_sold(pub_id, True)

    # 2) получаем публикацию и драфт
    pub = await repo.get_publication(pub_id)
    if not pub:
        await _edit_reply_msg_safely(call.message, t("myads_not_found"))
        return

    draft = await repo.get_draft(pub.draft_id)
    if not draft:
        await _edit_reply_msg_safely(call.message, t("myads_not_found"))
        return

    # 3) пересобираем подпись и добавляем бейдж "ПРОДАНО"
    me = await call.bot.get_me()
    base_caption = await _build_caption(
        draft,
        t,
        seller_username=call.from_user.username,
        seller_id=call.from_user.id,
        bot_username=me.username,
    )
    sold_badge = "🔴 ПРОДАНО"
    new_caption = f"{sold_badge}\n{base_caption}"

    # 4) пытаемся обновить пост(ы) в канале
    ok = False
    if pub.channel_id and pub.message_ids_json:
        first_msg_id = int(pub.message_ids_json[0])
        ok = await _edit_channel_post_safely(call.bot, int(pub.channel_id), first_msg_id, new_caption)

    # 5) финальный ответ пользователю (редактируем то сообщение, где была кнопка)
    if ok:
        await _edit_reply_msg_safely(call.message, t("myads_marked_sold"))
    else:
        await _edit_reply_msg_safely(call.message, t("myads_marked_sold") + " (пост в канале не удалось обновить)")


@router.callback_query(F.data.startswith("myads:del:"))
async def my_ads_delete(call: CallbackQuery, repo: Repository, t):
    await call.answer()
    pub_id = int(call.data.split(":")[2])
    await repo.delete_publication(pub_id)
    await _edit_reply_msg_safely(call.message, t("myads_deleted"))
