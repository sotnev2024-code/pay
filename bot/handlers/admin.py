from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import admin_menu_kb, back_admin_kb
from config import settings
from database import crud
from database.engine import async_session

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_tariff_data = State()
    waiting_promo_data = State()
    waiting_broadcast = State()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer("🔧 <b>Админ-панель</b>", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("🔧 <b>Админ-панель</b>", reply_markup=admin_menu_kb())
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
async def cb_tariffs(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        tariffs = await crud.get_active_tariffs(session)

    if not tariffs:
        text = "🏷 <b>Тарифы</b>\n\nТарифов пока нет."
    else:
        lines = ["🏷 <b>Тарифы</b>\n"]
        for t in tariffs:
            lines.append(
                f"#{t.id} <b>{t.name}</b> — "
                f"⭐{t.price_stars} / {t.price_rub}₽ / ${t.price_usd} "
                f"({t.duration_days or '∞'} дн.)"
            )
        text = "\n".join(lines)

    text += (
        "\n\n<i>Для добавления тарифа отправьте данные в формате:</i>\n"
        "<code>название | описание | stars | rub | usd | дни | тип</code>\n"
        "<i>Типы: subscription, one_time, membership</i>"
    )

    await callback.message.edit_text(text, reply_markup=back_admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_promos")
async def cb_promos(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        promos = await crud.get_all_promo_codes(session)

    if not promos:
        text = "🎟 <b>Промокоды</b>\n\nПромокодов нет."
    else:
        lines = ["🎟 <b>Промокоды</b>\n"]
        for p in promos:
            status = "✅" if p.is_active else "❌"
            disc = f"-{p.discount_percent}%" if p.discount_percent else f"-{p.discount_amount}"
            lines.append(f"{status} <code>{p.code}</code> {disc} ({p.used_count}/{p.max_uses or '∞'})")
        text = "\n".join(lines)

    text += (
        "\n\n<i>Для добавления промокода отправьте:</i>\n"
        "<code>promo КОД | процент | сумма | макс_использований</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_payments")
async def cb_payments(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        payments = await crud.get_recent_payments(session, limit=10)

    if not payments:
        text = "💰 <b>Платежи</b>\n\nПлатежей пока нет."
    else:
        lines = ["💰 <b>Последние платежи</b>\n"]
        for p in payments:
            u_name = p.user.username or str(p.user.telegram_id) if p.user else "?"
            status_icon = {"success": "✅", "pending": "⏳", "failed": "❌", "refunded": "🔄"}.get(
                p.status.value, "❓"
            )
            lines.append(
                f"{status_icon} @{u_name} — {p.amount} {p.currency} "
                f"({p.provider}) {p.created_at.strftime('%d.%m %H:%M')}"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=back_admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\nОтправьте текст сообщения для рассылки всем пользователям:",
        reply_markup=back_admin_kb(),
    )
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.answer()


@router.message(AdminStates.waiting_broadcast)
async def handle_broadcast(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return

    await state.clear()

    from bot.bot_instance import bot

    async with async_session() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(crud.User.telegram_id)
        )
        user_ids = [row[0] for row in result.all()]

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, message.text)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 Рассылка завершена!\n"
        f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        reply_markup=admin_menu_kb(),
    )


@router.message(F.text.startswith("promo "))
async def handle_add_promo(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return

    try:
        parts = message.text[6:].split("|")
        code = parts[0].strip()
        percent = int(parts[1].strip()) if len(parts) > 1 else 0
        amount = float(parts[2].strip()) if len(parts) > 2 else 0
        max_uses = int(parts[3].strip()) if len(parts) > 3 else None

        async with async_session() as session:
            promo = await crud.create_promo_code(
                session,
                code=code,
                discount_percent=percent,
                discount_amount=amount,
                max_uses=max_uses,
            )
        await message.answer(f"✅ Промокод <code>{promo.code}</code> создан!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
