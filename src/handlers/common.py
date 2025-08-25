from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..db.repo import Repository
from ..keyboards.reply import main_menu_kb, back_only_kb
from ..services.i18n_filters import TextKey
from ..config import Settings

router = Router()


# ========================== /start ==========================
@router.message(F.text == "/start")
async def cmd_start(message: Message, t, repo: Optional[Repository] = None) -> None:
    """Приветствие и главное меню. repo опционален."""
    market = "-"
    general_username = "-"

    if repo is not None:
        try:
            app_settings = await repo.get_settings()  # type: ignore[attr-defined]
            if app_settings:
                market = getattr(app_settings, "publish_channel", None) \
                         or getattr(app_settings, "market_chat_id", None) or "-"
                general_username = getattr(app_settings, "general_chat_username", None) or "-"
        except Exception:
            pass

    hello = t("hello_username").format(
        username=(message.from_user.username or message.from_user.full_name or "")
    )
    channels = (
        f"{t('our_channels')}\n\n"
        f"{t('bikemarket')} — {market}\n"
        f"{t('general_chat')} — {general_username}"
    )
    rules = f"\n\n{t('rules')} — {t('rules_hint')}"

    await message.answer(f"{hello}\n\n{channels}{rules}", reply_markup=main_menu_kb(t))


# ======================= Личный профиль ======================
@router.message(TextKey("btn_profile"))
async def show_profile(message: Message, t, repo: Optional[Repository] = None) -> None:
    """Карточка профиля. Если БД недоступна — показываем фолбэк без статистики."""
    def _fmt_hms(secs: int) -> str:
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    if repo is None:
        lang_label = t("lang_ru") if (message.from_user.language_code or "ru").startswith("ru") else t("lang_ky")
        text = (
            f"<b>{t('profile_title')}</b>\n"
            f"Username: @{message.from_user.username or '-'}\n"
            f"{t('profile_lang')}: {lang_label}\n"
            f"{t('profile_total')}: 0\n"
            f"{t('profile_next_in')}: 00:00:00"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=back_only_kb(t))
        return

    user = await repo.create_or_get_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    # всего опубликованных
    try:
        total = await repo.count_user_published_total(user.id)  # type: ignore[attr-defined]
    except Exception:
        total = 0

    # время до следующей публикации (если слотов нет)
    next_in = "00:00:00"
    try:
        ul = await repo.get_user_limit(user.id)  # type: ignore[attr-defined]
        if ul:
            # Безлимит или есть свободные слоты -> можно публиковать сейчас
            if ul.mode == "unlimited" or ul.quota_total is None:
                next_in = "00:00:00"
            else:
                free = max(0, (ul.quota_total or 0) - (ul.quota_used or 0))
                if free > 0:
                    next_in = "00:00:00"
                else:
                    now = datetime.now(timezone.utc)
                    exp = ul.expires_at
                    if exp and exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp and exp > now:
                        secs = int((exp - now).total_seconds())
                        next_in = _fmt_hms(max(0, secs))
                    else:
                        next_in = "00:00:00"
    except Exception:
        pass

    lang_label = t("lang_ru") if (user.lang or "ru") == "ru" else t("lang_ky")

    text = (
        f"<b>{t('profile_title')}</b>\n"
        f"Username: @{message.from_user.username or '-'}\n"
        f"{t('profile_lang')}: {lang_label}\n"
        f"{t('profile_total')}: {total}\n"
        f"{t('profile_next_in')}: {next_in}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=back_only_kb(t))


# =================== Выбор языка (полный цикл) =================
@router.message(TextKey("btn_language"))
async def menu_language(message: Message, t) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("lang_ru"), callback_data="lang:set:ru")
    kb.button(text=t("lang_ky"), callback_data="lang:set:ky")
    kb.adjust(2)
    await message.answer(t("choose_language"), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("lang:set:"))
async def set_language(call: CallbackQuery, i18n, t, repo: Optional[Repository] = None):
    lang = call.data.split(":")[-1]

    # Сохраняем язык для текущего пользователя (по ВНУТРЕННЕМУ user.id)
    if repo is not None:
        try:
            db_user = await repo.create_or_get_user(
                telegram_id=call.from_user.id,
                username=call.from_user.username,
                first_name=getattr(call.from_user, "first_name", None),
                last_name=getattr(call.from_user, "last_name", None),
            )
            await repo.set_user_lang(db_user.id, lang)  # 👈 правильный id
        except Exception:
            pass

    # создаём переводчик на выбранном языке — интерфейс сменится сразу
    t_now = i18n.get_translator(lang)
    if lang == "ru":
        await call.message.edit_text(t_now("language_set_ru"))
    else:
        await call.message.edit_text(t_now("language_set_ky"))

    await call.message.answer(t_now("main_menu_title"), reply_markup=main_menu_kb(t_now))
    await call.answer()


# ===================== Назад в главное меню ====================
@router.message(TextKey("back"))
async def back_to_main(message: Message, t) -> None:
    await message.answer(t("main_menu_title"), reply_markup=main_menu_kb(t))

@router.message(TextKey("btn_settings"))
async def open_settings(message: Message, t, repo: Optional[Repository] = None, settings: Optional[Settings] = None):
    is_admin = bool(settings and message.from_user and message.from_user.id == settings.admin_id)
    if not is_admin:
        # Заглушка для обычных юзеров
        # (ключ добавлен ниже в YAML; если забудешь — покажется сам ключ)
        await message.answer(t("settings_stub"))
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("admin_users_btn"), callback_data="admin:users")],
        [InlineKeyboardButton(text=t("admin_limit_btn"), callback_data="admin:limit")],
        [InlineKeyboardButton(text=t("admin_rules_btn"), callback_data="admin:rules")],
        [InlineKeyboardButton(text=t("btn_admin_payments"), callback_data="admin:payments")],
    ])
    await message.answer(t("settings_stub"), reply_markup=kb)