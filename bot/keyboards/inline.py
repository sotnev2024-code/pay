from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import settings


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
        [
            InlineKeyboardButton(text="🏷 Тарифы", callback_data="admin_tariffs"),
            InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos"),
        ],
        [InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
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
