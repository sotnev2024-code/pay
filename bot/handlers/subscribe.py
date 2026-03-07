from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from config import settings

router = Router()


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🛒 Открыть магазин",
                web_app=WebAppInfo(url=settings.webapp_url),
            )]
        ]
    )
    await message.answer(
        "Нажмите кнопку ниже, чтобы выбрать тариф и оформить подписку:",
        reply_markup=kb,
    )
