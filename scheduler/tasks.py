from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import InlineKeyboardMarkup

from bot.bot_instance import bot
from bot.keyboards.inline import COLOR_EMOJI, make_colored_button
from bot.services.subscription import deactivate_subscription
from database import crud
from database.engine import async_session
from database.models import AutoBroadcastTriggerType, User

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


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
                btn_color_key = ab.button_color or "green"
                emoji = COLOR_EMOJI.get(btn_color_key, "🟢")
                text = f"{emoji} {ab.button_text}"
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            make_colored_button(
                                text,
                                url=ab.button_url,
                                color_key=btn_color_key,
                            )
                        ]
                    ]
                )
            for uid in user_ids:
                if await crud.was_auto_broadcast_sent(session, uid, ab.id):
                    continue
                user = await session.get(User, uid)
                if not user:
                    continue
                try:
                    text = ab.message_text_html or "(пусто)"
                    if ab.trigger_type == AutoBroadcastTriggerType.DAYS_BEFORE_EXPIRY:
                        sub = await crud.get_subscription_expiring_in_days_for_user(
                            session, uid, ab.trigger_value
                        )
                        if sub and sub.tariff:
                            text = text.replace("{tariff_name}", sub.tariff.name)
                        text = text.replace("{days}", str(ab.trigger_value))

                    if ab.message_photo_file_id:
                        await bot.send_photo(
                            user.telegram_id,
                            ab.message_photo_file_id,
                            caption=text,
                            parse_mode="HTML",
                            reply_markup=kb,
                        )
                    else:
                        await bot.send_message(
                            user.telegram_id,
                            text,
                            parse_mode="HTML",
                            reply_markup=kb,
                        )
                    await crud.mark_auto_broadcast_sent(session, uid, ab.id)
                except Exception as e:
                    logger.warning("Auto broadcast %s to user %s failed: %s", ab.id, uid, e)


def start_scheduler() -> None:
    scheduler.add_job(expire_subscriptions, "interval", minutes=30, id="expire_subs")
    scheduler.add_job(process_auto_broadcasts, "interval", minutes=15, id="auto_broadcasts")
    scheduler.start()
    logger.info("Scheduler started")
