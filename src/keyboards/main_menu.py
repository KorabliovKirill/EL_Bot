from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu(has_clans: bool = False, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Возвращает главное меню
    
    Args:
        has_clans: есть ли у пользователя привязанные кланы
        is_admin: является ли пользователь администратором
    """
    kb = [
        [KeyboardButton(text="📚 Информация по домашкам")],
        [KeyboardButton(text="⏰ Истекающие домашки")],
    ]
    
    # Кнопка обновления доступна только наставникам с кланами
    if has_clans:
        kb.append([KeyboardButton(text="🔄 Обновить мои домашки")])
    
    # Кнопка админ-панели доступна только администраторам
    if is_admin:
        kb.append([KeyboardButton(text="🔧 Админ-панель")])
    
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)