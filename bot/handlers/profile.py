from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import main_menu_kb, profile_kb
from database.crud import get_active_subscription, get_user_by_telegram_id
from database.engine import async_session

router = Router()


async def _profile_text(telegram_id: int) -> str:
    async with async_session() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if user is None:
            return "Вы не зарегистрированы. Нажмите /start"

        sub = await get_active_subscription(session, user.id)

        text = f"👤 <b>Профиль</b>\nID: <code>{user.telegram_id}</code>\n"
        if user.username:
            text += f"Username: @{user.username}\n"

        if sub:
            text += f"\n✅ <b>Подписка активна</b>\n"
            text += f"Тариф: <b>{sub.tariff.name}</b>\n"
            if sub.expires_at:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                days_left = (sub.expires_at.replace(tzinfo=timezone.utc) - now).days
                text += f"Осталось дней: <b>{max(days_left, 0)}</b>\n"
                text += f"Истекает: {sub.expires_at.strftime('%d.%m.%Y')}\n"
            else:
                text += "Бессрочная подписка\n"
        else:
            text += "\n❌ <b>Подписка не активна</b>\n"
            text += "Оформите подписку, чтобы получить доступ."

    return text


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    text = await _profile_text(message.from_user.id)
    await message.answer(text, reply_markup=profile_kb())


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery) -> None:
    text = await _profile_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=profile_kb())
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        f"👋 Привет, <b>{callback.from_user.first_name}</b>!\n\n"
        "Выберите действие:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
