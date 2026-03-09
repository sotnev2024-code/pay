from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.bot_instance import bot
from bot.keyboards.inline import (
    COLOR_EMOJI,
    admin_button_color_kb,
    admin_main_menu_kb,
    admin_menu_kb,
    admin_promos_list_kb,
    admin_tariffs_list_kb,
    autob_add_confirm_kb,
    autob_button_color_kb,
    autob_button_yn_kb,
    autob_delay_type_kb,
    autob_trigger_kb,
    autob_url_skip_kb,
    auto_broadcast_list_kb,
    back_admin_kb,
    broadcast_audience_kb,
    broadcast_button_color_kb,
    broadcast_button_yn_kb,
    broadcast_confirm_kb,
    broadcast_url_skip_kb,
    make_colored_button,
    promo_del_confirm_kb,
    promo_discount_type_kb,
    promo_edit_fields_kb,
    promo_limit_type_kb,
    skip_kb,
    tariff_del_confirm_kb,
    tariff_duration_unit_kb,
    tariff_duration_value_kb,
    tariff_edit_fields_kb,
    tariff_type_kb,
)
from config import settings
from sqlalchemy import select

from database import crud
from database.engine import async_session
from database.models import (
    AutoBroadcastTriggerType,
    PaymentStatus,
    PromoCode,
    TariffType,
    User,
)

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_tariff_data = State()
    waiting_promo_data = State()
    waiting_broadcast = State()
    waiting_main_photo = State()
    waiting_main_desc = State()
    waiting_main_btn_text = State()
    waiting_main_btn_color = State()
    # Add tariff
    waiting_tariff_type = State()
    waiting_tariff_name = State()
    waiting_tariff_desc = State()
    waiting_tariff_price = State()
    waiting_tariff_dur_unit = State()
    waiting_tariff_dur_val = State()
    # Edit tariff field
    waiting_tariff_edit = State()
    # Add promo
    waiting_promo_code = State()
    waiting_promo_disc_type = State()
    waiting_promo_disc_value = State()
    waiting_promo_limit_type = State()
    waiting_promo_limit_value = State()
    # Edit promo field
    waiting_promo_edit = State()
    # Broadcast
    waiting_broadcast_msg = State()
    waiting_broadcast_audience = State()
    waiting_broadcast_button_yn = State()
    waiting_broadcast_btn_text = State()
    waiting_broadcast_btn_color = State()
    waiting_broadcast_btn_url = State()
    waiting_broadcast_confirm = State()
    # Auto broadcast add
    waiting_autob_trigger = State()
    waiting_autob_trigger_value = State()
    waiting_autob_msg = State()
    waiting_autob_delay_type = State()
    waiting_autob_delay_value = State()
    waiting_autob_button_yn = State()
    waiting_autob_btn_text = State()
    waiting_autob_btn_color = State()
    waiting_autob_btn_url = State()
    waiting_autob_confirm = State()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer("🔧 <b>Админ-панель</b>", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("🔧 <b>Админ-панель</b>", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_main_menu")
async def cb_admin_main_menu(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with async_session() as session:
        menu = await crud.get_main_menu_settings(session)
    text_preview = menu.description_html or "Привет! Добро пожаловать."
    await callback.message.edit_text(
        "📋 <b>Главное меню</b>\n\nТекущее сообщение (превью ниже):",
        reply_markup=admin_main_menu_kb(),
    )
    if menu.photo_file_id:
        await callback.message.answer_photo(
            menu.photo_file_id,
            caption=text_preview[:1024],
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(text_preview[:4096], parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_main_photo")
async def cb_admin_main_photo(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🖼 Отправьте фото для главного меню:",
        reply_markup=back_admin_kb(),
    )
    await state.set_state(AdminStates.waiting_main_photo)
    await callback.answer()


@router.callback_query(F.data == "admin_main_desc")
async def cb_admin_main_desc(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📝 Отправьте описание главного меню (поддерживается HTML):",
        reply_markup=back_admin_kb(),
    )
    await state.set_state(AdminStates.waiting_main_desc)
    await callback.answer()


@router.callback_query(F.data == "admin_main_btn")
async def cb_admin_main_btn(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🔘 Введите новое название кнопки:",
        reply_markup=back_admin_kb(),
    )
    await state.set_state(AdminStates.waiting_main_btn_text)
    await callback.answer()


@router.message(AdminStates.waiting_main_photo, F.photo)
async def handle_main_photo(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    file_id = message.photo[-1].file_id
    async with async_session() as session:
        await crud.update_main_menu_settings(session, photo_file_id=file_id)
    await state.clear()
    await message.answer("✅ Фото главного меню обновлено.", reply_markup=admin_menu_kb())


@router.message(AdminStates.waiting_main_desc, F.text)
async def handle_main_desc(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    async with async_session() as session:
        # Сохраняем описание в виде HTML, чтобы сохранить форматирование
        html = message.html_text or message.text or ""
        await crud.update_main_menu_settings(session, description_html=html)
    await state.clear()
    await message.answer("✅ Описание обновлено.", reply_markup=admin_menu_kb())


@router.message(AdminStates.waiting_main_btn_text, F.text)
async def handle_main_btn_text(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(main_btn_text=message.text)
    await state.set_state(AdminStates.waiting_main_btn_color)
    await message.answer(
        "Выберите цвет кнопки:",
        reply_markup=admin_button_color_kb(),
    )


@router.callback_query(
    F.data.startswith("admin_color:"),
    StateFilter(AdminStates.waiting_main_btn_color),
)
async def cb_admin_color(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    color = callback.data.replace("admin_color:", "")
    data = await state.get_data()
    btn_text = data.get("main_btn_text", "Оформить подписку")
    await state.clear()
    async with async_session() as session:
        await crud.update_main_menu_settings(
            session, button_text=btn_text, button_color=color
        )
    await callback.message.edit_text(
        "✅ Название и цвет кнопки обновлены.",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def cb_stats(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        total_users = await crud.count_users(session)
        active_subs = await crud.count_active_subscriptions(session)
        now = datetime.now(timezone.utc)
        revenue_30d = await crud.get_revenue(session, since=now - timedelta(days=30))
        revenue_total = await crud.get_revenue(session)

    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"✅ Активных подписок: <b>{active_subs}</b>\n"
        f"💰 Доход за 30 дней: <b>{revenue_30d:.2f}</b>\n"
        f"💰 Доход всего: <b>{revenue_total:.2f}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_tariffs")
async def cb_tariffs(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    async with async_session() as session:
        tariffs = await crud.get_active_tariffs(session)
    text = "🏷 <b>Тарифы</b>\n\nВыберите действие:"
    await callback.message.edit_text(text, reply_markup=admin_tariffs_list_kb(tariffs))
    await callback.answer()


@router.callback_query(F.data.startswith("tariff_sel:"))
async def cb_tariff_sel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    tariff_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        tariff = await crud.get_tariff_by_id(session, tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    is_sub = tariff.tariff_type == TariffType.SUBSCRIPTION
    text = (
        f"🏷 <b>{tariff.name}</b>\n\n"
        f"Описание: {tariff.description or '—'}\n"
        f"Цена: {tariff.price_rub}₽\n"
        f"Длительность: {tariff.duration_days or '∞'} дн.\n\n"
        "Выберите, что изменить:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=tariff_edit_fields_kb(tariff_id, is_sub),
    )
    await callback.answer()


def _duration_days(unit: str, value: int) -> int:
    if unit == "day":
        return value
    if unit == "week":
        return value * 7
    if unit == "month":
        return value * 30
    return value * 365


@router.callback_query(F.data == "admin_tariff_add")
async def cb_tariff_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "Выберите вариант:\n\n• Подписка — с периодом (дни/недели/месяцы/годы)\n• Полный доступ — разовый платёж",
        reply_markup=tariff_type_kb(),
    )
    await state.set_state(AdminStates.waiting_tariff_type)
    await callback.answer()


@router.callback_query(F.data.startswith("tariff_add_type:"), StateFilter(AdminStates.waiting_tariff_type))
async def cb_tariff_add_type(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    if callback.data == "admin_tariffs":
        await state.clear()
        await cb_tariffs(callback, state)
        return
    typ = callback.data.replace("tariff_add_type:", "")
    await state.update_data(tariff_type=typ)
    await state.set_state(AdminStates.waiting_tariff_name)
    await callback.message.edit_text("Введите название тарифа:", reply_markup=back_admin_kb())
    await callback.answer()


@router.message(AdminStates.waiting_tariff_name, F.text)
async def handle_tariff_name(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(tariff_name=message.text)
    await state.set_state(AdminStates.waiting_tariff_desc)
    await message.answer(
        "Введите описание (опционально):",
        reply_markup=skip_kb(),
    )


@router.callback_query(F.data == "tariff_add_skip", StateFilter(AdminStates.waiting_tariff_desc))
async def cb_tariff_skip_desc(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.update_data(tariff_desc="")
    await state.set_state(AdminStates.waiting_tariff_price)
    await callback.message.edit_text("Введите стоимость (в рублях):", reply_markup=back_admin_kb())
    await callback.answer()


@router.message(AdminStates.waiting_tariff_desc, F.text)
async def handle_tariff_desc(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(tariff_desc=message.text or "")
    await state.set_state(AdminStates.waiting_tariff_price)
    await message.answer("Введите стоимость (в рублях):", reply_markup=back_admin_kb())


@router.message(AdminStates.waiting_tariff_price, F.text)
async def handle_tariff_price(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    try:
        rub = float(message.text.replace(",", ".").strip())
        if rub <= 0:
            raise ValueError("Число должно быть больше 0")
    except ValueError as e:
        await message.answer(f"❌ Введите число: {e}")
        return
    await state.update_data(tariff_price_rub=rub)
    data = await state.get_data()
    typ = data.get("tariff_type", "subscription")
    if typ == "subscription":
        await state.set_state(AdminStates.waiting_tariff_dur_unit)
        await message.answer("Выберите единицу срока:", reply_markup=tariff_duration_unit_kb())
    else:
        async with async_session() as session:
            tariffs = await crud.get_active_tariffs(session)
            sort_order = max((t.sort_order for t in tariffs), default=0) + 1
        stars = max(1, int(rub / 6))
        usd = round(rub / 100, 2)
        async with async_session() as session:
            await crud.create_tariff(
                session,
                name=data.get("tariff_name", "Тариф"),
                description=data.get("tariff_desc", ""),
                price_stars=stars,
                price_rub=rub,
                price_usd=usd,
                duration_days=None,
                tariff_type=TariffType.ONE_TIME,
                sort_order=sort_order,
            )
        await state.clear()
        await message.answer("✅ Тариф «Полный доступ» создан.", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("tariff_dur_unit:"), StateFilter(AdminStates.waiting_tariff_dur_unit))
async def cb_tariff_dur_unit(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    unit = callback.data.replace("tariff_dur_unit:", "")
    await state.update_data(tariff_dur_unit=unit)
    await state.set_state(AdminStates.waiting_tariff_dur_val)
    await callback.message.edit_text(
        "Выберите количество:",
        reply_markup=tariff_duration_value_kb(unit),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tariff_dur_val:"), StateFilter(AdminStates.waiting_tariff_dur_val))
async def cb_tariff_dur_val(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    value = int(callback.data.replace("tariff_dur_val:", ""))
    data = await state.get_data()
    unit = data.get("tariff_dur_unit", "day")
    duration_days = _duration_days(unit, value)
    rub = data.get("tariff_price_rub", 0)
    stars = max(1, int(rub / 6))
    usd = round(rub / 100, 2)
    async with async_session() as session:
        tariffs = await crud.get_active_tariffs(session)
        sort_order = max((t.sort_order for t in tariffs), default=0) + 1
        await crud.create_tariff(
            session,
            name=data.get("tariff_name", "Тариф"),
            description=data.get("tariff_desc", ""),
            price_stars=stars,
            price_rub=rub,
            price_usd=usd,
            duration_days=duration_days,
            tariff_type=TariffType.SUBSCRIPTION,
            sort_order=sort_order,
        )
    await state.clear()
    await callback.message.edit_text("✅ Тариф создан.", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("tariff_edit:"))
async def cb_tariff_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    tariff_id, field = int(parts[1]), parts[2]
    await state.update_data(edit_tariff_id=tariff_id, edit_tariff_field=field)
    await state.set_state(AdminStates.waiting_tariff_edit)
    labels = {"name": "название", "desc": "описание", "price": "стоимость (руб)", "duration": "длительность (дней)"}
    await callback.message.edit_text(
        f"Введите новое значение для поля «{labels.get(field, field)}»:",
        reply_markup=back_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_tariff_edit, F.text)
async def handle_tariff_edit_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    tariff_id = data.get("edit_tariff_id")
    field = data.get("edit_tariff_field")
    if not tariff_id or not field:
        await state.clear()
        return
    kwargs = {}
    if field == "name":
        kwargs["name"] = message.text
    elif field == "desc":
        kwargs["description"] = message.text
    elif field == "price":
        try:
            rub = float(message.text.replace(",", ".").strip())
            kwargs["price_rub"] = rub
            kwargs["price_stars"] = max(1, int(rub / 6))
            kwargs["price_usd"] = round(rub / 100, 2)
        except ValueError:
            await message.answer("❌ Введите число.")
            return
    elif field == "duration":
        try:
            kwargs["duration_days"] = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Введите целое число дней.")
            return
    async with async_session() as session:
        await crud.update_tariff(session, tariff_id, **kwargs)
    await state.clear()
    async with async_session() as session:
        tariff = await crud.get_tariff_by_id(session, tariff_id)
    is_sub = tariff and tariff.tariff_type == TariffType.SUBSCRIPTION
    text = f"✅ Обновлено.\n\n🏷 <b>{tariff.name}</b>\n\nВыберите, что изменить:"
    await message.answer(text, reply_markup=tariff_edit_fields_kb(tariff_id, is_sub))


@router.callback_query(F.data.startswith("tariff_del:"))
async def cb_tariff_del(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    tariff_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "Удалить этот тариф? (он станет неактивным)",
        reply_markup=tariff_del_confirm_kb(tariff_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tariff_del_confirm:"))
async def cb_tariff_del_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    tariff_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        await crud.delete_tariff(session, tariff_id)
    await callback.message.edit_text("✅ Тариф отключён.", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_promos")
async def cb_promos(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    async with async_session() as session:
        promos = await crud.get_all_promo_codes(session)
    text = "🎟 <b>Промокоды</b>\n\nВыберите действие:"
    await callback.message.edit_text(text, reply_markup=admin_promos_list_kb(promos))
    await callback.answer()


@router.callback_query(F.data.startswith("promo_sel:"))
async def cb_promo_sel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    promo_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        promo = await session.get(PromoCode, promo_id)
    if not promo:
        await callback.answer("Промокод не найден", show_alert=True)
        return
    p = promo
    disc = f"-{p.discount_percent}%" if p.discount_percent else f"-{p.discount_amount}₽"
    limit = f"{p.used_count}/{p.max_uses}" if p.max_uses else ("до " + p.valid_until.strftime("%d.%m.%Y") if p.valid_until else "∞")
    text = (
        f"🎟 <b>{p.code}</b>\n\n"
        f"Скидка: {disc}\n"
        f"Ограничение: {limit}\n"
        f"Статус: {'✅' if p.is_active else '❌'}\n\n"
        "Выберите, что изменить:"
    )
    has_percent = True
    has_amount = True
    has_max_uses = p.max_uses is not None
    has_valid_until = p.valid_until is not None
    await callback.message.edit_text(
        text,
        reply_markup=promo_edit_fields_kb(promo_id, has_percent, has_amount, has_max_uses, has_valid_until),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_promo_add")
async def cb_promo_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "Введите промокод (латиница/цифры):",
        reply_markup=back_admin_kb(),
    )
    await state.set_state(AdminStates.waiting_promo_code)
    await callback.answer()


@router.message(AdminStates.waiting_promo_code, F.text)
async def handle_promo_code(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    code = (message.text or "").strip().upper()
    if not code:
        await message.answer("Введите непустой промокод.")
        return
    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.waiting_promo_disc_type)
    await message.answer("Выберите вариант скидки:", reply_markup=promo_discount_type_kb())


@router.callback_query(F.data.startswith("promo_add_disc:"), StateFilter(AdminStates.waiting_promo_disc_type))
async def cb_promo_disc_type(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    if callback.data == "admin_promos":
        await state.clear()
        await cb_promos(callback, state)
        return
    disc = callback.data.replace("promo_add_disc:", "")
    await state.update_data(promo_disc_type=disc)
    await state.set_state(AdminStates.waiting_promo_disc_value)
    if disc == "percent":
        await callback.message.edit_text("Введите процент скидки (число):", reply_markup=back_admin_kb())
    else:
        await callback.message.edit_text("Введите сумму скидки (число):", reply_markup=back_admin_kb())
    await callback.answer()


@router.message(AdminStates.waiting_promo_disc_value, F.text)
async def handle_promo_disc_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    disc_type = data.get("promo_disc_type", "amount")
    try:
        val = float(message.text.replace(",", ".").strip())
        if disc_type == "percent" and (val <= 0 or val > 100):
            raise ValueError("Процент от 1 до 100")
        if disc_type == "amount" and val < 0:
            raise ValueError("Сумма ≥ 0")
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return
    if disc_type == "percent":
        await state.update_data(promo_discount_percent=int(val), promo_discount_amount=0.0)
    else:
        await state.update_data(promo_discount_amount=val, promo_discount_percent=0)
    await state.set_state(AdminStates.waiting_promo_limit_type)
    await message.answer("Выберите ограничение:", reply_markup=promo_limit_type_kb())


@router.callback_query(F.data.startswith("promo_add_limit:"), StateFilter(AdminStates.waiting_promo_limit_type))
async def cb_promo_limit_type(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    if callback.data == "admin_promos":
        await state.clear()
        await cb_promos(callback, state)
        return
    limit = callback.data.replace("promo_add_limit:", "")
    await state.update_data(promo_limit_type=limit)
    await state.set_state(AdminStates.waiting_promo_limit_value)
    if limit == "max_uses":
        await callback.message.edit_text("Введите максимальное количество активаций:", reply_markup=back_admin_kb())
    else:
        await callback.message.edit_text(
            "Введите срок действия (дата в формате ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ):",
            reply_markup=back_admin_kb(),
        )
    await callback.answer()


@router.message(AdminStates.waiting_promo_limit_value, F.text)
async def handle_promo_limit_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    limit_type = data.get("promo_limit_type", "max_uses")
    try:
        if limit_type == "max_uses":
            val = int(message.text.strip())
            if val < 1:
                raise ValueError("Число ≥ 1")
            async with async_session() as session:
                await crud.create_promo_code(
                    session,
                    code=data.get("promo_code", ""),
                    discount_percent=data.get("promo_discount_percent", 0),
                    discount_amount=data.get("promo_discount_amount", 0.0),
                    max_uses=val,
                    valid_until=None,
                )
        else:
            from datetime import datetime as dt
            parts = message.text.strip().split()
            date_str = parts[0]
            time_str = parts[1] if len(parts) > 1 else "23:59"
            d = dt.strptime(date_str, "%d.%m.%Y")
            t = dt.strptime(time_str, "%H:%M").time()
            valid_until = dt.combine(d.date(), t)
            if valid_until.tzinfo is None:
                from datetime import timezone
                valid_until = valid_until.replace(tzinfo=timezone.utc)
            async with async_session() as session:
                await crud.create_promo_code(
                    session,
                    code=data.get("promo_code", ""),
                    discount_percent=data.get("promo_discount_percent", 0),
                    discount_amount=data.get("promo_discount_amount", 0.0),
                    max_uses=None,
                    valid_until=valid_until,
                )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        return
    await state.clear()
    await message.answer("✅ Промокод создан.", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("promo_edit:"))
async def cb_promo_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    promo_id, field = int(parts[1]), parts[2]
    await state.update_data(edit_promo_id=promo_id, edit_promo_field=field)
    await state.set_state(AdminStates.waiting_promo_edit)
    labels = {
        "code": "промокод",
        "discount_percent": "процент скидки",
        "discount_amount": "сумма скидки",
        "max_uses": "макс. активаций",
        "valid_until": "срок действия (ДД.ММ.ГГГГ)",
    }
    await callback.message.edit_text(
        f"Введите новое значение для «{labels.get(field, field)}»:",
        reply_markup=back_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_promo_edit, F.text)
async def handle_promo_edit_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    promo_id = data.get("edit_promo_id")
    field = data.get("edit_promo_field")
    if not promo_id or not field:
        await state.clear()
        return
    kwargs = {}
    if field == "code":
        kwargs["code"] = message.text.strip().upper()
    elif field == "discount_percent":
        kwargs["discount_percent"] = int(float(message.text.replace(",", ".")))
    elif field == "discount_amount":
        kwargs["discount_amount"] = float(message.text.replace(",", "."))
    elif field == "max_uses":
        kwargs["max_uses"] = int(message.text.strip())
    elif field == "valid_until":
        from datetime import datetime as dt, timezone
        d = dt.strptime(message.text.strip(), "%d.%m.%Y").replace(tzinfo=timezone.utc)
        kwargs["valid_until"] = d
    try:
        async with async_session() as session:
            await crud.update_promo_code(session, promo_id, **kwargs)
    except Exception as e:
        await message.answer(f"❌ {e}")
        return
    await state.clear()
    async with async_session() as session:
        promo = await session.get(PromoCode, promo_id)
    if not promo:
        await message.answer("Промокод не найден.", reply_markup=admin_menu_kb())
        return
    has_percent = promo.discount_percent is not None and promo.discount_percent > 0
    has_amount = promo.discount_amount is not None and promo.discount_amount > 0
    if not has_percent and not has_amount:
        has_percent = has_amount = True
    text = f"✅ Обновлено.\n\n🎟 <b>{promo.code}</b>\n\nВыберите, что изменить:"
    await message.answer(
        text,
        reply_markup=promo_edit_fields_kb(
            promo_id, has_percent, has_amount,
            promo.max_uses is not None, promo.valid_until is not None,
        ),
    )


@router.callback_query(F.data.startswith("promo_del:"))
async def cb_promo_del(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    promo_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "Удалить промокод? (он станет неактивным)",
        reply_markup=promo_del_confirm_kb(promo_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("promo_del_confirm:"))
async def cb_promo_del_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    promo_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        await crud.delete_promo_code(session, promo_id)
    await callback.message.edit_text("✅ Промокод отключён.", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_payments")
async def cb_payments(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    from io import BytesIO
    from openpyxl import Workbook
    from aiogram.types import BufferedInputFile

    async with async_session() as session:
        payments = await crud.get_payments_for_export(session, status=PaymentStatus.SUCCESS)

    wb = Workbook()
    ws = wb.active
    ws.title = "Платежи"
    ws.append(["ID", "Дата", "Telegram ID", "Username", "Сумма", "Валюта", "Провайдер", "Тариф", "Статус"])
    for p in payments:
        u = p.user
        t = p.tariff
        ws.append([
            p.id,
            p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
            u.telegram_id if u else "",
            (u.username or "") if u else "",
            p.amount,
            p.currency or "",
            p.provider or "",
            t.name if t else "",
            p.status.value if p.status else "",
        ])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    doc = BufferedInputFile(buf.getvalue(), filename="payments.xlsx")
    await callback.message.answer_document(doc, caption="💰 Выгрузка успешных платежей")
    await callback.message.edit_text(
        "💰 Файл с платежами отправлен выше.",
        reply_markup=back_admin_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\nОтправьте сообщение: текст, фото или фото с подписью (поддерживается HTML):",
        reply_markup=back_admin_kb(),
    )
    await state.set_state(AdminStates.waiting_broadcast_msg)
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_msg, F.content_type.in_({"text", "photo"}))
async def handle_broadcast_msg(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    photo_file_id = None
    text = ""
    if message.photo:
        photo_file_id = message.photo[-1].file_id
        # Фото с подписью – используем HTML-представление подписи
        text = message.html_caption or message.caption or ""
    else:
        # Обычное текстовое сообщение – HTML-представление текста
        text = message.html_text or message.text or ""
    await state.update_data(broadcast_photo=photo_file_id, broadcast_text=text)
    await state.set_state(AdminStates.waiting_broadcast_audience)
    await message.answer("Кому отправить?", reply_markup=broadcast_audience_kb())


@router.callback_query(F.data.startswith("broadcast_aud:"), StateFilter(AdminStates.waiting_broadcast_audience))
async def cb_broadcast_audience(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    if callback.data == "admin_menu":
        await state.clear()
        await cb_admin_menu(callback, state)
        return
    aud = callback.data.replace("broadcast_aud:", "")
    await state.update_data(broadcast_audience=aud)
    await state.set_state(AdminStates.waiting_broadcast_button_yn)
    await callback.message.edit_text("Добавить кнопку к сообщению?", reply_markup=broadcast_button_yn_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_btn:"), StateFilter(AdminStates.waiting_broadcast_button_yn))
async def cb_broadcast_button_yn(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    yes = callback.data == "broadcast_btn:yes"
    await state.update_data(broadcast_has_button=yes)
    if yes:
        await state.set_state(AdminStates.waiting_broadcast_btn_text)
        await callback.message.edit_text("Введите название кнопки:", reply_markup=back_admin_kb())
    else:
        await _broadcast_show_preview(callback.message, state)
        await state.set_state(AdminStates.waiting_broadcast_confirm)
        await callback.message.answer("Превью выше. Подтвердите отправку:", reply_markup=broadcast_confirm_kb())
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_btn_text, F.text)
async def handle_broadcast_btn_text(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(broadcast_btn_text=message.text)
    await state.set_state(AdminStates.waiting_broadcast_btn_color)
    await message.answer("Выберите цвет кнопки:", reply_markup=broadcast_button_color_kb())


@router.callback_query(F.data.startswith("broadcast_color:"), StateFilter(AdminStates.waiting_broadcast_btn_color))
async def cb_broadcast_color(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    color = callback.data.replace("broadcast_color:", "")
    await state.update_data(broadcast_btn_color=color)
    await state.set_state(AdminStates.waiting_broadcast_btn_url)
    await callback.message.edit_text(
        "Введите ссылку для кнопки:",
        reply_markup=broadcast_url_skip_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "broadcast_url_skip", StateFilter(AdminStates.waiting_broadcast_btn_url))
async def cb_broadcast_url_skip(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.update_data(broadcast_btn_url=settings.webapp_url)
    await _broadcast_show_preview(callback.message, state)
    await state.set_state(AdminStates.waiting_broadcast_confirm)
    await callback.message.answer("Превью выше. Подтвердите отправку:", reply_markup=broadcast_confirm_kb())
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_btn_url, F.text)
async def handle_broadcast_btn_url(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(broadcast_btn_url=message.text.strip())
    await _broadcast_show_preview(message, state)
    await state.set_state(AdminStates.waiting_broadcast_confirm)
    await message.answer("Превью выше. Подтвердите отправку:", reply_markup=broadcast_confirm_kb())


async def _broadcast_show_preview(message: Message, state: FSMContext) -> None:
    from aiogram.types import InlineKeyboardMarkup

    data = await state.get_data()
    photo = data.get("broadcast_photo")
    text = data.get("broadcast_text") or "(пусто)"
    has_btn = data.get("broadcast_has_button")
    if has_btn:
        btn_text = data.get("broadcast_btn_text", "Кнопка")
        btn_color = data.get("broadcast_btn_color", "green")
        emoji = COLOR_EMOJI.get(btn_color, "🟢")
        url = data.get("broadcast_btn_url") or settings.webapp_url
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    make_colored_button(
                        f"{emoji} {btn_text}",
                        url=url,
                        color_key=btn_color,
                    )
                ]
            ]
        )
    else:
        kb = None
    if photo:
        await message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("broadcast_confirm:"), StateFilter(AdminStates.waiting_broadcast_confirm))
async def cb_broadcast_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    if callback.data != "broadcast_confirm:yes":
        await state.clear()
        await callback.message.edit_text("Рассылка отменена.", reply_markup=admin_menu_kb())
        await callback.answer()
        return
    data = await state.get_data()
    async with async_session() as session:
        aud = data.get("broadcast_audience", "all")
        if aud == "all":
            user_ids = await crud.get_user_ids_all(session)
        elif aud == "paid":
            user_ids = await crud.get_user_ids_paid(session)
        elif aud == "expired":
            user_ids = await crud.get_user_ids_subscription_expired(session)
        else:
            user_ids = await crud.get_user_ids_never_paid(session)
    photo = data.get("broadcast_photo")
    text = data.get("broadcast_text") or ""
    has_btn = data.get("broadcast_has_button")
    if has_btn:
        from aiogram.types import InlineKeyboardMarkup

        btn_text = data.get("broadcast_btn_text", "Кнопка")
        btn_color = data.get("broadcast_btn_color", "green")
        emoji = COLOR_EMOJI.get(btn_color, "🟢")
        url = data.get("broadcast_btn_url") or settings.webapp_url
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    make_colored_button(
                        f"{emoji} {btn_text}",
                        url=url,
                        color_key=btn_color,
                    )
                ]
            ]
        )
    else:
        kb = None
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            if photo:
                await bot.send_photo(uid, photo, caption=text or None, parse_mode="HTML", reply_markup=kb)
            else:
                await bot.send_message(uid, text or "(пусто)", parse_mode="HTML", reply_markup=kb)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await callback.message.edit_text(
        f"📢 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


# ── Auto broadcasts ──────────────────────────────────────────────────

@router.callback_query(F.data == "admin_auto_broadcast")
async def cb_admin_auto_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    async with async_session() as session:
        broadcasts = await crud.get_all_auto_broadcasts(session)
    await callback.message.edit_text(
        "⏰ <b>Автоматические рассылки</b>\n\nВыберите действие:",
        reply_markup=auto_broadcast_list_kb(broadcasts),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("autob_sel:"))
async def cb_autob_sel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    bid = int(callback.data.split(":")[1])
    async with async_session() as session:
        b = await crud.get_auto_broadcast_by_id(session, bid)
    if not b:
        await callback.answer("Не найдено", show_alert=True)
        return
    from bot.keyboards.inline import _auto_broadcast_trigger_label
    label = _auto_broadcast_trigger_label(b)
    text = f"⏰ Рассылка #{b.id}\n\nТриггер: {label}\nЗадержка: {b.delay_value} {b.delay_type}\nАктивна: {'да' if b.is_active else 'нет'}"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())
    await callback.answer()


@router.callback_query(F.data == "autob_add")
async def cb_autob_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "В каком случае отправлять?",
        reply_markup=autob_trigger_kb(),
    )
    await state.set_state(AdminStates.waiting_autob_trigger)
    await callback.answer()


@router.callback_query(F.data.startswith("autob_trigger:"), StateFilter(AdminStates.waiting_autob_trigger))
async def cb_autob_trigger(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    if callback.data == "admin_auto_broadcast":
        await state.clear()
        await cb_admin_auto_broadcast(callback, state)
        return
    trigger = callback.data.replace("autob_trigger:", "")
    await state.update_data(autob_trigger=trigger)
    if trigger in ("days_before_expiry", "after_payment_days"):
        await state.set_state(AdminStates.waiting_autob_trigger_value)
        await callback.message.edit_text(
            "Введите число N (дней):",
            reply_markup=back_admin_kb(),
        )
    else:
        await state.update_data(autob_trigger_value=0)
        await state.set_state(AdminStates.waiting_autob_msg)
        await callback.message.edit_text(
            "Отправьте сообщение для рассылки (текст, фото или фото с подписью, HTML):",
            reply_markup=back_admin_kb(),
        )
    await callback.answer()


@router.message(AdminStates.waiting_autob_trigger_value, F.text)
async def handle_autob_trigger_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    try:
        n = int(message.text.strip())
        if n < 1:
            raise ValueError("N ≥ 1")
    except ValueError as e:
        await message.answer(f"❌ Введите целое число: {e}")
        return
    await state.update_data(autob_trigger_value=n)
    await state.set_state(AdminStates.waiting_autob_msg)
    await message.answer(
        "Отправьте сообщение для рассылки (текст, фото или фото с подписью, HTML):",
        reply_markup=back_admin_kb(),
    )


@router.message(AdminStates.waiting_autob_msg, F.content_type.in_({"text", "photo"}))
async def handle_autob_msg(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    photo = message.photo[-1].file_id if message.photo else None
    if message.photo:
        text = message.html_caption or message.caption or ""
    else:
        text = message.html_text or message.text or ""
    await state.update_data(autob_photo=photo, autob_text=text)
    await state.set_state(AdminStates.waiting_autob_delay_type)
    await message.answer("Через какое время отправить?", reply_markup=autob_delay_type_kb())


@router.callback_query(F.data.startswith("autob_delay_type:"), StateFilter(AdminStates.waiting_autob_delay_type))
async def cb_autob_delay_type(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    dt = callback.data.replace("autob_delay_type:", "")
    await state.update_data(autob_delay_type=dt)
    await state.set_state(AdminStates.waiting_autob_delay_value)
    await callback.message.edit_text(
        f"Введите количество ({'часов' if dt == 'hours' else 'дней'}):",
        reply_markup=back_admin_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_autob_delay_value, F.text)
async def handle_autob_delay_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    try:
        n = int(message.text.strip())
        if n < 1:
            raise ValueError("Число ≥ 1")
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return
    await state.update_data(autob_delay_value=n)
    await state.set_state(AdminStates.waiting_autob_button_yn)
    await message.answer("Добавить кнопку?", reply_markup=autob_button_yn_kb())


@router.callback_query(F.data.startswith("autob_btn:"), StateFilter(AdminStates.waiting_autob_button_yn))
async def cb_autob_button_yn(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    yes = callback.data == "autob_btn:yes"
    await state.update_data(autob_has_button=yes)
    if yes:
        await state.set_state(AdminStates.waiting_autob_btn_text)
        await callback.message.edit_text("Введите название кнопки:", reply_markup=back_admin_kb())
    else:
        await state.update_data(autob_btn_text=None, autob_btn_color=None, autob_btn_url=None)
        await _autob_show_preview(callback.message, state)
        await state.set_state(AdminStates.waiting_autob_confirm)
        await callback.message.answer("Превью. Добавить рассылку?", reply_markup=autob_add_confirm_kb())
    await callback.answer()


@router.message(AdminStates.waiting_autob_btn_text, F.text)
async def handle_autob_btn_text(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(autob_btn_text=message.text)
    await state.set_state(AdminStates.waiting_autob_btn_color)
    await message.answer("Цвет кнопки:", reply_markup=autob_button_color_kb())


@router.callback_query(F.data.startswith("autob_color:"), StateFilter(AdminStates.waiting_autob_btn_color))
async def cb_autob_color(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    color = callback.data.replace("autob_color:", "")
    await state.update_data(autob_btn_color=color)
    await state.set_state(AdminStates.waiting_autob_btn_url)
    await callback.message.edit_text("Введите ссылку для кнопки:", reply_markup=autob_url_skip_kb())
    await callback.answer()


@router.callback_query(F.data == "autob_url_skip", StateFilter(AdminStates.waiting_autob_btn_url))
async def cb_autob_url_skip(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.update_data(autob_btn_url=settings.webapp_url)
    await _autob_show_preview(callback.message, state)
    await state.set_state(AdminStates.waiting_autob_confirm)
    await callback.message.answer("Превью. Добавить рассылку?", reply_markup=autob_add_confirm_kb())
    await callback.answer()


@router.message(AdminStates.waiting_autob_btn_url, F.text)
async def handle_autob_btn_url(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(autob_btn_url=message.text.strip())
    await _autob_show_preview(message, state)
    await state.set_state(AdminStates.waiting_autob_confirm)
    await message.answer("Превью. Добавить рассылку?", reply_markup=autob_add_confirm_kb())


async def _autob_show_preview(message: Message, state: FSMContext) -> None:
    from aiogram.types import InlineKeyboardMarkup

    data = await state.get_data()
    photo = data.get("autob_photo")
    text = data.get("autob_text") or "(пусто)"
    has_btn = data.get("autob_has_button")
    if has_btn and data.get("autob_btn_text"):
        btn_text = data.get("autob_btn_text", "Кнопка")
        btn_color = data.get("autob_btn_color", "green")
        emoji = COLOR_EMOJI.get(btn_color, "🟢")
        url = data.get("autob_btn_url") or settings.webapp_url
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    make_colored_button(
                        f"{emoji} {btn_text}",
                        url=url,
                        color_key=btn_color,
                    )
                ]
            ]
        )
    else:
        kb = None
    if photo:
        await message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("autob_add_confirm:"), StateFilter(AdminStates.waiting_autob_confirm))
async def cb_autob_add_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    if callback.data != "autob_add_confirm:yes":
        await state.clear()
        await callback.message.edit_text("Отменено.", reply_markup=admin_menu_kb())
        await callback.answer()
        return
    data = await state.get_data()
    trigger = data.get("autob_trigger", "after_start_no_payment")
    trigger_value = data.get("autob_trigger_value", 0)
    delay_type = data.get("autob_delay_type", "days")
    delay_value = data.get("autob_delay_value", 1)
    photo = data.get("autob_photo")
    text = data.get("autob_text", "")
    btn_text = data.get("autob_btn_text") if data.get("autob_has_button") else None
    btn_url = data.get("autob_btn_url") if data.get("autob_has_button") else None
    btn_color = data.get("autob_btn_color") if data.get("autob_has_button") else None
    try:
        trigger_enum = AutoBroadcastTriggerType(trigger)
    except ValueError:
        trigger_enum = AutoBroadcastTriggerType.AFTER_START_NO_PAYMENT
    async with async_session() as session:
        await crud.create_auto_broadcast(
            session,
            trigger_type=trigger_enum,
            trigger_value=trigger_value,
            delay_type=delay_type,
            delay_value=delay_value,
            message_photo_file_id=photo,
            message_text_html=text,
            button_text=btn_text,
            button_url=btn_url,
            button_color=btn_color,
        )
    await state.clear()
    await callback.message.edit_text("✅ Авторассылка добавлена.", reply_markup=admin_menu_kb())
    await callback.answer()


