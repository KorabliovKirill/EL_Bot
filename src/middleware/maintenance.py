"""
Middleware для проверки режима обслуживания
Блокирует обработку сообщений, когда бот находится в режиме обновления
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
import logging

from src.core.maintenance import maintenance_manager

logger = logging.getLogger(__name__)


class MaintenanceMiddleware(BaseMiddleware):
    """
    Middleware для блокировки команд во время обслуживания бота
    """
    
    # Команды, которые всегда разрешены (даже в maintenance mode)
    ALLOWED_COMMANDS = {'/start', '/help'}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Проверяет режим обслуживания перед обработкой сообщения
        """
        # Проверяем только сообщения
        if not isinstance(event, Message):
            return await handler(event, data)
        
        message: Message = event
        
        # Проверяем режим обслуживания
        is_maintenance = await maintenance_manager.is_maintenance_active()
        
        if not is_maintenance:
            # Режим обслуживания неактивен - продолжаем обработку
            return await handler(event, data)
        
        # Режим обслуживания активен
        # Разрешаем только определенные команды
        text = message.text or ""
        
        # Проверяем, является ли это разрешенной командой
        if any(text.startswith(cmd) for cmd in self.ALLOWED_COMMANDS):
            return await handler(event, data)
        
        # Получаем сообщение о блокировке
        maintenance_msg = await maintenance_manager.get_maintenance_message()
        
        # Отправляем сообщение о блокировке
        await message.answer(maintenance_msg)
        
        # НЕ вызываем handler - команда блокируется
        logger.info(
            f"Команда заблокирована (maintenance mode): "
            f"user={message.from_user.username}, text={text[:50]}"
        )
        
        # Возвращаем None - команда не обрабатывается
        return None
