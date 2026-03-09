from typing import Optional

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards.inline import main_menu_kb_from_settings
from database import crud
from database.engine import async_session
from database.models import MainMenuButton

router = Router()

DEFAULT_GREETING = (
    "👋 Привет, {name}!\n\n"
    "Добро пожаловать! Здесь вы можете оформить подписку "
    "и получить доступ к закрытому каналу.\n\n"
    "Выберите действие:"
)


async def send_main_menu(message: Message, first_name: Optional[str] = None) -> None:
    async with async_session() as session:
        menu = await crud.get_main_menu_settings(session)
        extra = await crud.get_main_menu_buttons(session)
        kb = main_menu_kb_from_settings(menu, extra_buttons=list(extra))

    caption_or_text = menu.description_html or DEFAULT_GREETING.format(
        name=first_name or "Пользователь"
    )
    if not menu.description_html and first_name:
        caption_or_text = (
            f"👋 Привет, <b>{first_name}</b>!\n\n"
            "Добро пожаловать! Здесь вы можете оформить подписку "
            "и получить доступ к закрытому каналу.\n\n"
            "Выберите действие:"
        )

    if menu.photo_file_id:
        await message.answer_photo(
            menu.photo_file_id,
            caption=caption_or_text,
            parse_mode="HTML",
            reply_markup=kb,
        )
    else:
        await message.answer(
            caption_or_text,
            parse_mode="HTML",
            reply_markup=kb,
        )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await send_main_menu(message, message.from_user.first_name)


@router.callback_query(F.data.startswith("main_btn_msg:"))
async def cb_main_btn_msg(callback: CallbackQuery) -> None:
    """
    Обработчик нажатия на кнопку главного меню с типом 'message'.
    Показывает сохранённый HTML-текст и кнопку 'Назад' в главное меню.
    """
    data = callback.data or ""
    try:
        _, raw_id = data.split(":", 1)
        btn_id = int(raw_id)
    except (ValueError, IndexError):
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    async with async_session() as session:
        btn = await session.get(MainMenuButton, btn_id)

    if not btn or btn.type != "message" or not btn.payload_html:
        await callback.answer("Сообщение недоступно.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ]
    )

    await callback.message.answer(
        btn.payload_html,
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()
