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
    return None

def _fix_label_spaces(s: str) -> str:
    # Грубая нормализация: вставим пробел после частых эмодзи/флагов
    for emo in ["💰","👀","🔄","🤏","🤙","🇰🇬","✅","❌"]:
        s = s.replace(emo, f"{emo} ")
    # Уберём двойные пробелы и края
    return " ".join(s.split())

def _type_badge(ad_type: str | None, t) -> str:
    m = {
        "sell": t("ad_type_sell"),    # в YAML уже с эмодзи
        "want": t("ad_type_want"),
        "trade": t("ad_type_trade"),
    }
    return m.get((ad_type or "").lower(), "")

def _city_badge(code: str | None, t) -> str:
    return t("city_bishkek") if code == "bishkek" else (t("city_osh") if code == "osh" else "")

def _delivery_line(code: str | None, t) -> str:
    if code == "country":
        return t("delivery_caption_country")
    if code == "no_ship":
        return t("delivery_caption_no_ship")
    return ""

async def _build_caption(
    draft,
    t,
    *,
    seller_username: str | None = None,
    seller_id: int | None = None,
    bot_username: str | None = None,
    sold: bool = False,
) -> str:
    """
    Формирует подпись к объявлению:
    - теги
    - первая строка с типом, состоянием и городом
    - название и описание
    - ПУСТАЯ СТРОКА
    - 'Цена | Доставка' (в одну строку)
    - ссылки: 💎 Разместить объявление, ✍️ Написать продавцу
    """
    # ----- теги -----
    tags: list[str] = []
    if draft.category:
        tags.append(f"#{draft.category}")
    if draft.subcategory:
        tags.append(f"#{draft.subcategory}")

    # ----- первая линия (тип | состояние | город | SOLD?) -----
    type_map = {"sell": "💰 Продаю", "want": "👀 Ищу", "trade": "🔄 Обмен"}
    type_label = type_map.get((draft.type or "").lower(), "💰 Продаю")

    cond_label = "🤙 Новый" if (draft.condition or "").lower() == "new" else "🤏 Б/У"
    city_label = "🇰🇬 Бишкек" if (draft.city or "") == "bishkek" else "🇰🇬 Ош"
    sold_label = "❌ ПРОДАНО" if sold or getattr(draft, "is_sold", False) else None

    header_bits = [type_label, cond_label, city_label]
    if sold_label:
        header_bits.append(sold_label)

    lines: list[str] = []
    if tags:
        lines.append(" ".join(tags))
    lines.append(" | ".join(header_bits))

    # ----- название и описания -----
    if draft.name:
        lines.append(f"<b>{draft.name}</b>")
    if draft.short_desc:
        lines.append(f"<i>{draft.short_desc}</i>")
    if draft.detail_desc:
        lines.append(draft.detail_desc)

    # ----- ПУСТАЯ строка перед ценой/доставкой -----
    meta_line_parts: list[str] = []

    # Цена
    if draft.price is not None:
        meta_line_parts.append(f"{int(draft.price)} KGS")

    # Доставка (в одной строке с ценой)
    delivery_str = None
    if (draft.delivery or "") == "country":
        # «🌎 По стране»
        delivery_str = t("delivery_country")
    elif (draft.delivery or "") == "no_ship":
        # «🚚 🙅 Не отправлю» (добавляем грузовичок к локализованной метке)
        delivery_str = f"🚚 {t('delivery_no_ship')}"
    if delivery_str:
        meta_line_parts.append(delivery_str)

    if meta_line_parts:
        lines.append("")  # пустая строка, чтобы не слипалось с описанием
        lines.append(" | ".join(meta_line_parts))

    # ----- ссылки -----
    def _seller_url(username: str | None, user_id: int | None) -> str | None:
        if username:
            return f"https://t.me/{username}"
        if user_id:
            return f"tg://user?id={user_id}"
        return None

    seller = _seller_url(seller_username, seller_id)
    link_lines: list[str] = []
    if bot_username:
        link_lines.append(f"💎 <a href='https://t.me/{bot_username}'>{t('post_link_post')}</a>")
    if seller:
        link_lines.append(f"✍️ <a href='{seller}'>{t('post_link_write_seller')}</a>")

    if link_lines:
        lines.append("")
        lines.extend(link_lines)

    return "\n".join(lines).strip()


async def send_preview(message: Message, draft, t) -> None:
    me = await message.bot.get_me()
    caption = await _build_caption(
        draft, t,
        seller_username=message.from_user.username if message.from_user else None,
        seller_id=message.from_user.id if message.from_user else None,
        bot_username=me.username,
        sold=False,
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
                photos[0].file_id, caption=caption, parse_mode="HTML",
                reply_markup=inline_kb.preview_keyboard(t)
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
        draft, t,
        seller_username=user.username, seller_id=user.telegram_id, bot_username=me.username,
        sold=False,
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
                m = await bot.send_photo(chat_id=chat_target, photo=photos[0].file_id,
                                         caption=caption, parse_mode="HTML", **kwargs)
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
        await repo.attach_publication_messages(publication.id, channel_id=channel_chat_id, message_ids=sent_message_ids)

    await state.clear()
    await call.message.answer(t("published_ok"), reply_markup=reply_kb.main_menu_kb(t))

@router.callback_query(F.data == "preview:cancel", AdCreation.Preview)
async def cancel_ad(call: CallbackQuery, repo: Repository, state: FSMContext, t) -> None:
    """Полная отмена: удаляем черновик и все фото, чтобы ничего не подтянулось в следующий раз.
       Не пытаемся редактировать медиасообщение текстом — отвечаем аккуратно.
    """
    await call.answer()
    data = await state.get_data()
    draft_id = data.get("draft_id")
    if draft_id:
        await repo.delete_draft(draft_id, only_if_status_draft=True)
    await state.clear()

    # безопасно пробуем редактировать подпись, затем текст, затем просто отвечаем
    try:
        await call.message.edit_caption(t("ad_cancelled"), parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(t("ad_cancelled"))
        except Exception:
            await call.message.answer(t("ad_cancelled"))
