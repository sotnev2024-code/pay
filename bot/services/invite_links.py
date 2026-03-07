from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from aiogram import Bot

logger = logging.getLogger(__name__)


async def create_invite_link(
    bot: Bot,
    channel_id: int,
    user_name: str = "",
    expire_hours: Optional[int] = None,
) -> Optional[str]:
    try:
        kwargs: dict = {
            "chat_id": channel_id,
            "member_limit": 1,
            "name": f"sub_{user_name}"[:32],
        }
        if expire_hours:
            kwargs["expire_date"] = datetime.now(timezone.utc) + timedelta(hours=expire_hours)

        link = await bot.create_chat_invite_link(**kwargs)
        return link.invite_link
    except Exception as e:
        logger.error("Failed to create invite link for channel %s: %s", channel_id, e)
        return None


async def revoke_invite_link(bot: Bot, channel_id: int, invite_link: str) -> bool:
    try:
        await bot.revoke_chat_invite_link(chat_id=channel_id, invite_link=invite_link)
        return True
    except Exception as e:
        logger.error("Failed to revoke invite link: %s", e)
        return False
