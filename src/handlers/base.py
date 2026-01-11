from aiogram.types import Message
from src.services.auth_service import is_authorized


async def check_authorization(message: Message) -> bool:
    username = message.from_user.username
    if not is_authorized(username):
        await message.answer("У вас нет доступа к этому боту.")
        return False
    return True