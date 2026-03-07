from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

router = Router()

HELP_TEXT = (
    "❓ <b>Помощь</b>\n\n"
    "<b>Доступные команды:</b>\n"
    "/start — главное меню\n"
    "/subscribe — оформить подписку\n"
    "/profile — статус вашей подписки\n"
    "/help — эта справка\n\n"
    "<b>Как оформить подписку?</b>\n"
    "1. Нажмите «Оформить подписку»\n"
    "2. Выберите тариф\n"
    "3. Выберите способ оплаты\n"
    "4. Оплатите\n"
    "5. Получите ссылку на канал\n\n"
    "По вопросам пишите администратору."
)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(HELP_TEXT)
    await callback.answer()
