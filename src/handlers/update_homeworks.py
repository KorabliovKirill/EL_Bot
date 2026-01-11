"""
Handler для обновления домашних заданий наставника
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction

from src.handlers.base import check_authorization
from src.services.auth_service import get_user_clan_ids
from src.services.homework_updater import update_homeworks_for_clans

router = Router(name="update_homeworks")

# Блокировка для предотвращения одновременных обновлений
_update_lock = set()


@router.message(F.text == "🔄 Обновить мои домашки")
async def handle_update_homeworks(message: Message):
    """Обработчик обновления домашних заданий"""
    
    # Проверка авторизации
    if not await check_authorization(message):
        return
    
    username = message.from_user.username
    user_id = message.from_user.id
    
    # Получаем кланы пользователя
    clan_ids = get_user_clan_ids(username)
    
    if not clan_ids:
        await message.answer(
            "❌ У вас нет привязанных кланов.\n"
            "Эта функция доступна только наставникам с кланами."
        )
        return
    
    # Проверка блокировки (пользователь уже обновляет)
    if user_id in _update_lock:
        await message.answer(
            "⏳ Обновление уже выполняется.\n"
            "Пожалуйста, дождитесь завершения предыдущего обновления."
        )
        return
    
    # Добавляем блокировку
    _update_lock.add(user_id)
    
    try:
        # Отправляем индикатор "печатает"
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # Информируем о начале обновления
        status_msg = await message.answer(
            f"🔄 Начинаю обновление домашних заданий...\n"
            f"Кланов для обновления: {len(clan_ids)}\n\n"
            f"⏳ Это может занять некоторое время, пожалуйста, ожидайте..."
        )
        
        # Выполняем обновление
        result = await update_homeworks_for_clans(clan_ids)
        
        # Отправляем результат
        if result["success"]:
            await message.answer(
                f"✅ Обновление завершено успешно!\n\n"
                f"📊 Статистика:\n"
                f"• Обновлено кланов: {result['updated_clans']}\n"
                f"• Загружено домашек: {result['total_homeworks']}\n\n"
                f"Данные обновлены и доступны в других разделах бота."
            )
        else:
            await message.answer(
                f"❌ Ошибка при обновлении:\n\n"
                f"{result.get('error', 'Неизвестная ошибка')}\n\n"
                f"Попробуйте повторить попытку позже или обратитесь к администратору."
            )
    
    except Exception as e:
        await message.answer(
            f"❌ Произошла непредвиденная ошибка:\n\n"
            f"{str(e)}\n\n"
            f"Пожалуйста, попробуйте позже."
        )
    
    finally:
        # Снимаем блокировку
        _update_lock.discard(user_id)
