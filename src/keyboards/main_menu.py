from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Информация по домашкам")],
        [KeyboardButton(text="Истекающие домашки")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)