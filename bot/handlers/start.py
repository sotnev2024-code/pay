from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards.inline import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "Добро пожаловать! Здесь вы можете оформить подписку "
        "и получить доступ к закрытому каналу.\n\n"
        "Выберите действие:",
        reply_markup=main_menu_kb(),
    )
