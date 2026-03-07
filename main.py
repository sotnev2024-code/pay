from __future__ import annotations

import asyncio
import logging

import uvicorn
# After uvicorn (which loads uvloop): force default policy so main thread has event loop on Python 3.8
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

from aiogram import types
from fastapi import Request

from bot.bot_instance import bot, dp
from bot.handlers import admin, help, payments, profile, start, subscribe
from bot.middlewares.user_register import UserRegisterMiddleware
from config import settings
from database.engine import engine
from database.models import Base
from payments.manager import init_providers, payment_manager
from scheduler.tasks import start_scheduler
from web.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def _register_routers() -> None:
    dp.update.outer_middleware(UserRegisterMiddleware())
    dp.include_router(start.router)
    dp.include_router(subscribe.router)
    dp.include_router(profile.router)
    dp.include_router(help.router)
    dp.include_router(payments.router)
    dp.include_router(admin.router)


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def _seed_demo_tariffs() -> None:
    """Create demo tariffs if the table is empty (first run convenience)."""
    from database.engine import async_session
    from database import crud

    async with async_session() as session:
        existing = await crud.get_active_tariffs(session)
        if existing:
            return

        await crud.create_tariff(
            session,
            name="Базовый",
            description="Доступ к основным материалам канала",
            price_stars=50,
            price_rub=299,
            price_usd=3,
            duration_days=30,
            tariff_type="subscription",
            features=["Доступ к каналу", "Архив материалов"],
            sort_order=1,
        )
        await crud.create_tariff(
            session,
            name="Про",
            description="Полный доступ + бонусные материалы",
            price_stars=150,
            price_rub=799,
            price_usd=8,
            duration_days=30,
            tariff_type="subscription",
            features=["Всё из Базового", "Бонусные материалы", "Приоритетная поддержка", "Вебинары"],
            sort_order=2,
        )
        await crud.create_tariff(
            session,
            name="VIP навсегда",
            description="Разовый платёж — доступ навсегда",
            price_stars=500,
            price_rub=2990,
            price_usd=29,
            duration_days=None,
            tariff_type="one_time",
            features=["Бессрочный доступ", "Все материалы", "Личные консультации", "VIP-чат"],
            sort_order=3,
        )
        logger.info("Demo tariffs created")


# ── Webhook mode ─────────────────────────────────────────────────────

async def on_startup_webhook() -> None:
    await _init_db()
    init_providers()
    logger.info("Payment providers: %s", ", ".join(payment_manager.available))
    _register_routers()

    webhook_url = settings.webhook_url + settings.webhook_path
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    logger.info("Webhook set to %s", webhook_url)

    start_scheduler()
    await _seed_demo_tariffs()


async def on_shutdown_webhook() -> None:
    from scheduler.tasks import scheduler as _sched
    _sched.shutdown(wait=False)
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("Bot shut down")


def run_webhook() -> None:
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(_app):  # noqa: ARG001
        await on_startup_webhook()
        yield
        await on_shutdown_webhook()

    app = create_app(lifespan=lifespan)

    @app.post(settings.webhook_path)
    async def telegram_webhook(request: Request):
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return {"ok": True}

    uvicorn.run(app, host="0.0.0.0", port=8000)


# ── Polling mode (local development) ─────────────────────────────────

async def run_polling() -> None:
    await _init_db()
    init_providers()
    logger.info("Payment providers: %s", ", ".join(payment_manager.available))
    _register_routers()

    await bot.delete_webhook(drop_pending_updates=True)

    start_scheduler()
    await _seed_demo_tariffs()

    # Start FastAPI in background (for Mini App API, if needed via ngrok)
    app = create_app()
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    async def start_web():
        await server.serve()

    web_task = asyncio.create_task(start_web())

    logger.info("Starting bot in POLLING mode...")
    logger.info("FastAPI running at http://localhost:8000")
    logger.info("Mini App available at http://localhost:8000/mini_app/")

    try:
        await dp.start_polling(bot)
    finally:
        server.should_exit = True
        await web_task
        await bot.session.close()


# ── Entry point ──────────────────────────────────────────────────────

def main() -> None:
    if settings.use_polling:
        logger.info("Mode: POLLING (local development)")
        asyncio.run(run_polling())
    else:
        logger.info("Mode: WEBHOOK (production)")
        run_webhook()


if __name__ == "__main__":
    main()
