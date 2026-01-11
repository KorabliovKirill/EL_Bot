# src/handlers/info.py

from aiogram import Router, F
from aiogram.types import Message

from src.handlers.base import check_authorization
from src.services.homework_service import get_homeworks_info
from src.utils.telegram import send_split_message      # ← новый импорт!

router = Router(name="info")


@router.message(F.text == "Информация по домашкам")
async def show_homeworks_info(message: Message):
    if not await check_authorization(message):
        return
    
    total, status = get_homeworks_info(message.from_user.username)
    
    # Отправляем возможно длинный total с разбиением
    await send_split_message(message, total)
    
    # status обычно короткий — можно оставить как есть
    await message.answer(status)