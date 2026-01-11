# src/bot.py

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from src.config.settings import TELEGRAM_TOKEN
from src.handlers import start, info, expiring, update_homeworks, admin
from src.middleware.maintenance import MaintenanceMiddleware

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(
        parse_mode="HTML"
    )
)

dp = Dispatcher()

# Подключаем middleware для режима обслуживания
dp.message.middleware(MaintenanceMiddleware())

# Подключаем роутеры
dp.include_router(start.router)
dp.include_router(info.router)
dp.include_router(expiring.router)
dp.include_router(update_homeworks.router)
dp.include_router(admin.router)