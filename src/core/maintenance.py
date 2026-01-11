"""
Система блокировки бота (maintenance mode)
Управляет состоянием обслуживания бота при обновлении баз данных
"""
import asyncio
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MaintenanceStatus:
    """Статус режима обслуживания"""
    is_active: bool = False
    operation: Optional[str] = None  # "homeworks" или "mentors"
    started_at: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # в минутах
    message: Optional[str] = None


class MaintenanceManager:
    """Менеджер режима обслуживания"""
    
    def __init__(self):
        self._status = MaintenanceStatus()
        self._lock = asyncio.Lock()
    
    async def is_maintenance_active(self) -> bool:
        """Проверяет, активен ли режим обслуживания"""
        async with self._lock:
            return self._status.is_active
    
    async def get_status(self) -> MaintenanceStatus:
        """Получает текущий статус"""
        async with self._lock:
            return MaintenanceStatus(
                is_active=self._status.is_active,
                operation=self._status.operation,
                started_at=self._status.started_at,
                estimated_duration=self._status.estimated_duration,
                message=self._status.message
            )
    
    async def start_maintenance(
        self, 
        operation: str, 
        estimated_duration: int,
        custom_message: Optional[str] = None
    ) -> bool:
        """
        Включает режим обслуживания
        
        Args:
            operation: тип операции ("homeworks" или "mentors")
            estimated_duration: примерная длительность в минутах
            custom_message: пользовательское сообщение
            
        Returns:
            True если удалось включить, False если уже активен
        """
        async with self._lock:
            if self._status.is_active:
                logger.warning(
                    f"Попытка включить maintenance mode, но он уже активен: {self._status.operation}"
                )
                return False
            
            self._status.is_active = True
            self._status.operation = operation
            self._status.started_at = datetime.now()
            self._status.estimated_duration = estimated_duration
            
            if custom_message:
                self._status.message = custom_message
            else:
                operation_names = {
                    "homeworks": "домашних заданий",
                    "mentors": "наставников"
                }
                op_name = operation_names.get(operation, "данных")
                self._status.message = (
                    f"🔧 Бот временно недоступен\n\n"
                    f"Выполняется обновление базы {op_name}.\n"
                    f"Примерное время: ~{estimated_duration} мин.\n\n"
                    f"Пожалуйста, подождите. Бот автоматически возобновит работу после завершения."
                )
            
            logger.info(
                f"Maintenance mode ВКЛЮЧЕН: {operation}, "
                f"длительность: {estimated_duration} мин"
            )
            return True
    
    async def stop_maintenance(self) -> bool:
        """
        Отключает режим обслуживания
        
        Returns:
            True если удалось отключить, False если не был активен
        """
        async with self._lock:
            if not self._status.is_active:
                logger.warning("Попытка отключить maintenance mode, но он не активен")
                return False
            
            operation = self._status.operation
            duration = None
            if self._status.started_at:
                duration = (datetime.now() - self._status.started_at).total_seconds() / 60
            
            self._status.is_active = False
            self._status.operation = None
            self._status.started_at = None
            self._status.estimated_duration = None
            self._status.message = None
            
            logger.info(
                f"Maintenance mode ВЫКЛЮЧЕН: {operation}, "
                f"фактическая длительность: {duration:.1f} мин" if duration else ""
            )
            return True
    
    async def get_maintenance_message(self) -> str:
        """Получает сообщение для пользователей"""
        async with self._lock:
            if not self._status.is_active:
                return "Бот работает в обычном режиме."
            
            return self._status.message or "🔧 Бот временно недоступен"


# Глобальный экземпляр менеджера
maintenance_manager = MaintenanceManager()
