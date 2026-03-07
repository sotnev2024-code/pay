from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.bot_instance import bot
from bot.services.subscription import deactivate_subscription
from database import crud
from database.engine import async_session

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


def start_scheduler() -> None:
    scheduler.add_job(check_expiring_subscriptions, "interval", minutes=30, id="check_expiring")
    scheduler.add_job(expire_subscriptions, "interval", minutes=30, id="expire_subs")
    scheduler.start()
    logger.info("Scheduler started")
