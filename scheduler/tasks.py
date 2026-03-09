from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.bot_instance import bot
from bot.keyboards.inline import COLOR_EMOJI
from bot.services.subscription import deactivate_subscription
from database import crud
from database.engine import async_session
from database.models import AutoBroadcastTriggerType, User

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_expiring_subscriptions() -> None:
    """Notify users whose subscriptions expire in 3 days or 1 day."""
    async with async_session() as session:
        subs_3d = await crud.get_expiring_subscriptions(session, within_days=3)
        for sub in subs_3d:
            if sub.notified_3d:
                continue
            try:
                days = (sub.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days
                if 1 < days <= 3:
                    await bot.send_message(
                        sub.user.telegram_id,
                        f"⏳ Ваша подписка <b>{sub.tariff.name}</b> заканчивается "
                        f"через <b>{days}</b> дн.\n\n"
                        "Продлите подписку: /subscribe",
                    )
                    sub.notified_3d = True
                    await session.commit()
            except Exception as e:
                logger.error("Notification error (3d): %s", e)

        subs_1d = await crud.get_expiring_subscriptions(session, within_days=1)
        for sub in subs_1d:
            if sub.notified_1d:
                continue
            try:
                await bot.send_message(
                    sub.user.telegram_id,
                    f"⚠️ Ваша подписка <b>{sub.tariff.name}</b> заканчивается "
                    f"<b>завтра</b>!\n\n"
                    "Продлите подписку, чтобы не потерять доступ: /subscribe",
                )
                sub.notified_1d = True
                await session.commit()
            except Exception as e:
                logger.error("Notification error (1d): %s", e)


async def expire_subscriptions() -> None:
    """Deactivate subscriptions that have passed their expiry date."""
    async with async_session() as session:
        expired = await crud.get_expired_subscriptions(session)
        for sub in expired:
            try:
                await deactivate_subscription(session, bot, sub)
                logger.info("Expired subscription #%s for user #%s", sub.id, sub.user_id)
            except Exception as e:
                logger.error("Error expiring sub #%s: %s", sub.id, e)


async def process_auto_broadcasts() -> None:
    """Send auto broadcasts by trigger type."""
    async with async_session() as session:
        broadcasts = await crud.get_all_auto_broadcasts(session)
        for ab in broadcasts:
            if not ab.is_active:
                continue
            if ab.trigger_type == AutoBroadcastTriggerType.DAYS_BEFORE_EXPIRY:
                user_ids = await crud.get_user_ids_expiring_in_days(session, ab.trigger_value)
            elif ab.trigger_type == AutoBroadcastTriggerType.AFTER_START_NO_PAYMENT:
                if ab.delay_type == "hours":
                    user_ids = await crud.get_user_ids_registered_before_no_payment(
                        session, delay_hours=ab.delay_value
                    )
                else:
                    user_ids = await crud.get_user_ids_registered_before_no_payment(
                        session, delay_days=ab.delay_value
                    )
            else:
                user_ids = await crud.get_user_ids_paid_days_ago(session, ab.trigger_value)
            kb = None
            if ab.button_text and ab.button_url:
                emoji = COLOR_EMOJI.get(ab.button_color or "green", "🟢")
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"{emoji} {ab.button_text}", url=ab.button_url)],
                ])
            for uid in user_ids:
                if await crud.was_auto_broadcast_sent(session, uid, ab.id):
                    continue
                user = await session.get(User, uid)
                if not user:
                    continue
                try:
                    if ab.message_photo_file_id:
                        await bot.send_photo(
                            user.telegram_id,
                            ab.message_photo_file_id,
                            caption=ab.message_text_html or None,
                            parse_mode="HTML",
                            reply_markup=kb,
                        )
                    else:
                        await bot.send_message(
                            user.telegram_id,
                            ab.message_text_html or "(пусто)",
                            parse_mode="HTML",
                            reply_markup=kb,
                        )
                    await crud.mark_auto_broadcast_sent(session, uid, ab.id)
                except Exception as e:
                    logger.warning("Auto broadcast %s to user %s failed: %s", ab.id, uid, e)


def start_scheduler() -> None:
    scheduler.add_job(check_expiring_subscriptions, "interval", minutes=30, id="check_expiring")
    scheduler.add_job(expire_subscriptions, "interval", minutes=30, id="expire_subs")
    scheduler.add_job(process_auto_broadcasts, "interval", minutes=15, id="auto_broadcasts")
    scheduler.start()
    logger.info("Scheduler started")
