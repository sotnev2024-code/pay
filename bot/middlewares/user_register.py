from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from config import settings
from database.crud import get_or_create_user
from database.engine import async_session


class UserRegisterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)

        user_obj = None
        if event.message and event.message.from_user:
            user_obj = event.message.from_user
        elif event.callback_query and event.callback_query.from_user:
            user_obj = event.callback_query.from_user
        elif event.pre_checkout_query and event.pre_checkout_query.from_user:
            user_obj = event.pre_checkout_query.from_user

        if user_obj:
            async with async_session() as session:
                db_user = await get_or_create_user(
                    session,
                    telegram_id=user_obj.id,
                    username=user_obj.username,
                    first_name=user_obj.first_name or "",
                    language_code=user_obj.language_code,
                    is_admin=user_obj.id in settings.admin_ids,
                )
                data["db_user"] = db_user
                data["session"] = session

        return await handler(event, data)
