from aiogram import Router, F
from aiogram.types import Message

from src.handlers.base import check_authorization
from src.services.homework_service import get_expiring_homeworks_text
from src.utils.telegram import send_split_message   # ← добавь этот импорт

router = Router(name="expiring")


@router.message(F.text == "Истекающие домашки")
async def show_expiring(message: Message):
    if not await check_authorization(message):
        return
    
    text = get_expiring_homeworks_text(message.from_user.username)
    
    await send_split_message(message, text)