"""
Клавиатуры для админ-панели
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_admin_menu() -> ReplyKeyboardMarkup:
    """
    Возвращает меню администратора
    
    Returns:
        ReplyKeyboardMarkup с кнопками админ-панели
    """
    kb = [
        [KeyboardButton(text="👤 Обновить базу наставников")],
        [KeyboardButton(text="📚 Обновить базу домашек")],
        [KeyboardButton(text="➕ Создать администратора")],
        [KeyboardButton(text="◀️ Назад в главное меню")],
    ]
    
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
