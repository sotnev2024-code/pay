from __future__ import annotations

from typing import Any, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import settings

COLOR_EMOJI = {"green": "🟢", "red": "🔴", "blue": "🔵", "white": "⚪"}


def _button_text_with_color(text: str, color: str) -> str:
    emoji = COLOR_EMOJI.get(color, "🟢")
    return f"{emoji} {text}"


def main_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text="🛒 Оформить подписку",
            web_app=WebAppInfo(url=settings.webapp_url),
        )],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_kb_from_settings(menu_settings: Any) -> InlineKeyboardMarkup:
    btn_text = getattr(menu_settings, "button_text", "Оформить подписку")
    btn_color = getattr(menu_settings, "button_color", "green")
    text = _button_text_with_color(btn_text, btn_color)
    buttons = [
        [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=settings.webapp_url))],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Изменить фото", callback_data="admin_main_photo")],
            [InlineKeyboardButton(text="📝 Изменить описание", callback_data="admin_main_desc")],
            [InlineKeyboardButton(text="🔘 Изменить название кнопки", callback_data="admin_main_btn")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")],
        ]
    )


def admin_button_color_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Зелёные", callback_data="admin_color:green"),
                InlineKeyboardButton(text="🔴 Красные", callback_data="admin_color:red"),
            ],
            [
                InlineKeyboardButton(text="🔵 Синие", callback_data="admin_color:blue"),
                InlineKeyboardButton(text="⚪ Белые", callback_data="admin_color:white"),
            ],
        ]
    )


def profile_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text="🔄 Продлить подписку",
            web_app=WebAppInfo(url=settings.webapp_url),
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📋 Главное меню", callback_data="admin_main_menu")],
        [
            InlineKeyboardButton(text="🏷 Тарифы", callback_data="admin_tariffs"),
            InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos"),
        ],
        [InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments")],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="⏰ Авто-рассылки", callback_data="admin_auto_broadcast")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_tariff_actions_kb(tariff_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"tariff_edit:{tariff_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"tariff_del:{tariff_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_tariffs")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_tariffs_list_kb(tariffs: list) -> InlineKeyboardMarkup:
    buttons = []
    for t in tariffs:
        buttons.append([
            InlineKeyboardButton(text=f"🏷 {t.name}", callback_data=f"tariff_sel:{t.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить тариф", callback_data="admin_tariff_add")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tariff_edit_fields_kb(tariff_id: int, is_subscription: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📌 Название", callback_data=f"tariff_edit:{tariff_id}:name")],
        [InlineKeyboardButton(text="📝 Описание", callback_data=f"tariff_edit:{tariff_id}:desc")],
        [InlineKeyboardButton(text="💰 Стоимость", callback_data=f"tariff_edit:{tariff_id}:price")],
    ]
    if is_subscription:
        buttons.append([
            InlineKeyboardButton(text="📅 Длительность", callback_data=f"tariff_edit:{tariff_id}:duration"),
        ])
    buttons.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"tariff_del:{tariff_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_tariffs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tariff_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Подписка", callback_data="tariff_add_type:subscription")],
            [InlineKeyboardButton(text="♾ Полный доступ", callback_data="tariff_add_type:one_time")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_tariffs")],
        ]
    )


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="tariff_add_skip")],
        ]
    )


def tariff_duration_unit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="День", callback_data="tariff_dur_unit:day"),
                InlineKeyboardButton(text="Неделя", callback_data="tariff_dur_unit:week"),
            ],
            [
                InlineKeyboardButton(text="Месяц", callback_data="tariff_dur_unit:month"),
                InlineKeyboardButton(text="Год", callback_data="tariff_dur_unit:year"),
            ],
        ]
    )


def _chunk(lst: list, size: int) -> list:
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def tariff_duration_value_kb(unit: str) -> InlineKeyboardMarkup:
    if unit == "day":
        nums = list(range(1, 31))
    elif unit == "week":
        nums = list(range(1, 5))
    elif unit == "month":
        nums = list(range(1, 13))
    else:
        nums = list(range(1, 6))
    rows = _chunk(
        [InlineKeyboardButton(text=str(n), callback_data=f"tariff_dur_val:{n}") for n in nums],
        5,
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tariff_del_confirm_kb(tariff_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"tariff_del_confirm:{tariff_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data="admin_tariffs"),
            ],
        ]
    )


# ── Promos ───────────────────────────────────────────────────────────

def admin_promos_list_kb(promos: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in promos:
        label = f"{'✅' if p.is_active else '❌'} {p.code}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"promo_sel:{p.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Добавить промокод", callback_data="admin_promo_add")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promo_edit_fields_kb(promo_id: int, has_percent: bool, has_amount: bool, has_max_uses: bool, has_valid_until: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📌 Промокод", callback_data=f"promo_edit:{promo_id}:code")],
    ]
    if has_percent:
        buttons.append([InlineKeyboardButton(text="📊 Процент", callback_data=f"promo_edit:{promo_id}:discount_percent")])
    if has_amount:
        buttons.append([InlineKeyboardButton(text="💰 Сумма", callback_data=f"promo_edit:{promo_id}:discount_amount")])
    if has_max_uses:
        buttons.append([InlineKeyboardButton(text="🔢 Лимит активаций", callback_data=f"promo_edit:{promo_id}:max_uses")])
    if has_valid_until:
        buttons.append([InlineKeyboardButton(text="📅 Срок действия", callback_data=f"promo_edit:{promo_id}:valid_until")])
    buttons.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"promo_del:{promo_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promos")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promo_discount_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Фикс. сумма", callback_data="promo_add_disc:amount")],
            [InlineKeyboardButton(text="Процент", callback_data="promo_add_disc:percent")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promos")],
        ]
    )


def promo_limit_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ограниченное кол-во активаций", callback_data="promo_add_limit:max_uses")],
            [InlineKeyboardButton(text="Срок действия", callback_data="promo_add_limit:valid_until")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promos")],
        ]
    )


def promo_del_confirm_kb(promo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"promo_del_confirm:{promo_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data="admin_promos"),
            ],
        ]
    )


# ── Broadcast ────────────────────────────────────────────────────────

def broadcast_audience_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Всем пользователям", callback_data="broadcast_aud:all")],
            [InlineKeyboardButton(text="Кто оплатил", callback_data="broadcast_aud:paid")],
            [InlineKeyboardButton(text="У кого закончилась подписка", callback_data="broadcast_aud:expired")],
            [InlineKeyboardButton(text="Кто не оплатил", callback_data="broadcast_aud:never_paid")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")],
        ]
    )


def broadcast_button_yn_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="broadcast_btn:yes")],
            [InlineKeyboardButton(text="Нет", callback_data="broadcast_btn:no")],
        ]
    )


def broadcast_button_color_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Зелёные", callback_data="broadcast_color:green"),
                InlineKeyboardButton(text="🔴 Красные", callback_data="broadcast_color:red"),
            ],
            [
                InlineKeyboardButton(text="🔵 Синие", callback_data="broadcast_color:blue"),
                InlineKeyboardButton(text="⚪ Белые", callback_data="broadcast_color:white"),
            ],
        ]
    )


def broadcast_url_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="broadcast_url_skip")],
        ]
    )


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm:yes")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_confirm:no")],
        ]
    )


# ── Auto broadcast ───────────────────────────────────────────────────

def auto_broadcast_list_kb(broadcasts: list) -> InlineKeyboardMarkup:
    buttons = []
    for b in broadcasts:
        label = f"{'✅' if b.is_active else '❌'} #{b.id} {_auto_broadcast_trigger_label(b)}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"autob_sel:{b.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Добавить рассылку", callback_data="autob_add")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _auto_broadcast_trigger_label(b: Any) -> str:
    tt = getattr(b, "trigger_type", None)
    if tt is None:
        return "?"
    v = getattr(tt, "value", str(tt))
    if v == "days_before_expiry":
        return f"За {b.trigger_value} дн. до конца"
    if v == "after_start_no_payment":
        return "После старта без оплаты"
    if v == "after_payment_days":
        return f"Через {b.trigger_value} дн. после оплаты"
    return v


def autob_trigger_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="До N дней до окончания", callback_data="autob_trigger:days_before_expiry")],
            [InlineKeyboardButton(text="После запуска бота и не оплаты", callback_data="autob_trigger:after_start_no_payment")],
            [InlineKeyboardButton(text="После оплаты спустя N дней", callback_data="autob_trigger:after_payment_days")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_auto_broadcast")],
        ]
    )


def autob_delay_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать часы", callback_data="autob_delay_type:hours")],
            [InlineKeyboardButton(text="Выбрать дни", callback_data="autob_delay_type:days")],
        ]
    )


def autob_add_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Добавить рассылку", callback_data="autob_add_confirm:yes")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="autob_add_confirm:no")],
        ]
    )


def autob_button_yn_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="autob_btn:yes")],
            [InlineKeyboardButton(text="Нет", callback_data="autob_btn:no")],
        ]
    )


def autob_button_color_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Зелёные", callback_data="autob_color:green"),
                InlineKeyboardButton(text="🔴 Красные", callback_data="autob_color:red"),
            ],
            [
                InlineKeyboardButton(text="🔵 Синие", callback_data="autob_color:blue"),
                InlineKeyboardButton(text="⚪ Белые", callback_data="autob_color:white"),
            ],
        ]
    )


def autob_url_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="autob_url_skip")],
        ]
    )


def back_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
        ]
    )


def channel_link_kb(invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Перейти в канал", url=invite_link)]
        ]
    )
