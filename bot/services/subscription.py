from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import channel_link_kb
from bot.services.invite_links import create_invite_link, revoke_invite_link
from config import settings
from database import crud
from database.models import PaymentStatus, Subscription, User

logger = logging.getLogger(__name__)


async def activate_subscription(
    session: AsyncSession,
    bot: Bot,
    user_id: int,
    tariff_id: int,
    payment_id: int,
) -> Optional[Subscription]:
    tariff = await crud.get_tariff_by_id(session, tariff_id)
    if tariff is None:
        return None

    user = await session.get(User, user_id)
    if user is None:
        return None

    channel_id = settings.channel_ids[0] if settings.channel_ids else None
    invite_link = None
    if channel_id:
        invite_link = await create_invite_link(
            bot, channel_id, user_name=user.username or str(user.telegram_id)
        )

    sub = await crud.create_subscription(
        session,
        user_id=user.id,
        tariff_id=tariff.id,
        duration_days=tariff.duration_days,
        invite_link=invite_link,
        channel_id=channel_id,
    )

    await crud.update_payment_status(session, payment_id, PaymentStatus.SUCCESS)

    try:
        text = (
            f"🎉 <b>Оплата прошла успешно!</b>\n\n"
            f"Тариф: <b>{tariff.name}</b>\n"
        )
        if tariff.duration_days:
            text += f"Срок: <b>{tariff.duration_days} дн.</b>\n"
        if invite_link:
            text += "\nНажмите кнопку ниже, чтобы перейти в канал:"
            await bot.send_message(
                user.telegram_id, text, reply_markup=channel_link_kb(invite_link)
            )
        else:
            text += "\nДоступ активирован!"
            await bot.send_message(user.telegram_id, text)
    except Exception as e:
        logger.error("Failed to notify user %s: %s", user.telegram_id, e)

    return sub


async def deactivate_subscription(
    session: AsyncSession, bot: Bot, sub: Subscription
) -> None:
    # Получаем пользователя заранее, чтобы знать его telegram_id
    user = await session.get(User, sub.user_id)

    # 1) Отзываем инвайт‑ссылку, чтобы по старой ссылке нельзя было войти
    if sub.invite_link and sub.channel_id:
        try:
            await revoke_invite_link(bot, sub.channel_id, sub.invite_link)
        except Exception as e:
            logger.error("Failed to revoke invite link for sub %s: %s", sub.id, e)

    # 2) Удаляем пользователя из канала/чата, если знаем его telegram_id и канал
    if user and sub.channel_id:
        try:
            # Приём: баним и сразу разбаниваем, чтобы удалить участника и
            # при этом не блокировать повторный вход при новой подписке.
            await bot.ban_chat_member(sub.channel_id, user.telegram_id)
            await bot.unban_chat_member(sub.channel_id, user.telegram_id)
        except Exception as e:
            logger.error(
                "Failed to remove user %s from channel %s on expiry: %s",
                user.telegram_id,
                sub.channel_id,
                e,
            )

    # 3) Помечаем подписку как истекшую в БД
    await crud.expire_subscription(session, sub.id)

    # 4) Уведомляем пользователя
    if user:
        try:
            await bot.send_message(
                user.telegram_id,
                "⏰ <b>Ваша подписка истекла.</b>\n"
                "Вы можете продлить её, нажав /subscribe",
            )
        except Exception as e:
            logger.error("Failed to notify user about expiry: %s", e)
