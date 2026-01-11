# src/bot.py

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties   # ← добавьте этот импорт

from src.config.settings import TELEGRAM_TOKEN
from src.handlers import start, info, expiring, update_homeworks

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(
        parse_mode="HTML"          # можно убрать, если хотите отправлять без форматирования по умолчанию
    )
)

dp = Dispatcher()

# Подключаем роутеры
dp.include_router(start.router)
dp.include_router(info.router)
dp.include_router(expiring.router)
dp.include_router(update_homeworks.router)