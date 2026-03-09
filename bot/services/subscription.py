from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import channel_link_kb
from bot.services.invite_links import create_invite_link, revoke_invite_link
from config import settings
from database import crud
from database.models import PaymentStatus, Subscription, User

logger = logging.getLogger(__name__)


def _format_template(text: str, **kwargs: str) -> str:
    for k, v in kwargs.items():
        text = text.replace("{" + k + "}", str(v) if v is not None else "")
    return text


async def _get_template_text(session, key: str, **kwargs: str) -> str:
    t = await crud.get_text_template_by_key(session, key)
    if t and t.text_html:
        return _format_template(t.text_html, **kwargs)
    return ""


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

    invite_link = None
    is_renewal = False
    new_expires = None

    # Логика продления/апгрейда подписки
    existing = await crud.get_active_subscription(session, user.id)
    now = datetime.now(timezone.utc)

    sub: Optional[Subscription]

    # Новый тариф бессрочный (навсегда)
    is_new_lifetime = tariff.duration_days is None

    if existing and existing.expires_at is None:
        # Уже есть бессрочная подписка — просто помечаем платёж успешным.
        sub = existing
    elif existing and not is_new_lifetime and existing.expires_at is not None:
        # Есть активная временная подписка, и покупается ещё один срок.
        # Продлеваем от текущей даты окончания (если она в будущем), либо от сейчас.
        base_start = existing.expires_at if existing.expires_at > now else now
        new_expires = base_start + timedelta(days=tariff.duration_days or 0)

        existing.expires_at = new_expires
        existing.tariff_id = tariff.id
        # Сбрасываем флаги уведомлений, чтобы напоминания сработали для нового срока
        existing.notified_3d = False
        existing.notified_1d = False
        await session.commit()
        await session.refresh(existing)
        sub = existing
        is_renewal = True
    else:
        # Либо подписки нет, либо была временная и покупается "навсегда":
        if existing:
            await crud.expire_subscription(session, existing.id)

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
        if existing and existing.expires_at is None:
            pass
        elif is_renewal and sub:
            text = await _get_template_text(
                session,
                "renew_success",
                tariff_name=tariff.name,
                expires_at=new_expires.strftime("%d.%m.%Y") if new_expires else "",
            )
            if text:
                await bot.send_message(user.telegram_id, text)
        elif invite_link:
            dur = f"{tariff.duration_days} дн." if tariff.duration_days else "бессрочно"
            text = await _get_template_text(
                session,
                "payment_success",
                tariff_name=tariff.name,
                duration_days=dur,
            )
            if text:
                await bot.send_message(
                    user.telegram_id, text, reply_markup=channel_link_kb(invite_link)
                )
            else:
                await bot.send_message(
                    user.telegram_id,
                    f"🎉 <b>Оплата прошла!</b>\nТариф: {tariff.name}\n\nПерейдите в канал:",
                    reply_markup=channel_link_kb(invite_link),
                )
        else:
            text = await _get_template_text(
                session, "payment_success_no_channel", tariff_name=tariff.name
            )
            if text:
                await bot.send_message(user.telegram_id, text)
            else:
                await bot.send_message(
                    user.telegram_id,
                    f"🎉 <b>Оплата прошла!</b>\nТариф: {tariff.name}\nДоступ активирован!",
                )
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
            text = await _get_template_text(session, "subscription_expired")
            if not text:
                text = "⏰ <b>Ваша подписка истекла.</b>\nВы можете продлить её, нажав /subscribe"
            await bot.send_message(user.telegram_id, text)
        except Exception as e:
            logger.error("Failed to notify user about expiry: %s", e)
