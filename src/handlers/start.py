from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.keyboards.main_menu import get_main_menu
from src.services.auth_service import is_authorized, get_user_clan_ids

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message):
    username = message.from_user.username
    
    if is_authorized(username):
        # Проверяем, есть ли у пользователя кланы
        clan_ids = get_user_clan_ids(username)
        has_clans = len(clan_ids) > 0
        
        await message.answer(
            "Добро пожаловать в помощник проверки ДЗ!\n\n"
            "Доступные команды:",
            reply_markup=get_main_menu(has_clans=has_clans)
        )
    else:
        await message.answer(
            "Доступ запрещён.\n"
            "Ваш username не найден в списке наставников/админов."
        )