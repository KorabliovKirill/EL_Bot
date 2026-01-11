"""
Сервис для управления администраторами
"""
import json
from pathlib import Path
from datetime import datetime
from src.config.settings import DATA_DIR

ADMINS_FILE = DATA_DIR / "admins.json"


class AdminServiceError(Exception):
    """Ошибка при работе с администраторами"""
    pass


def create_admin(admin_data: dict) -> dict:
    """
    Создает нового администратора
    
    Args:
        admin_data: словарь с данными администратора
        {
            "first_name": str,
            "last_name": str,
            "telegram_tag": str,
            "email": Optional[str],
            "phone": Optional[str],
            "telegram_id": Optional[int]
        }
        
    Returns:
        dict с информацией о результате:
        {
            "success": bool,
            "admin": Optional[dict],
            "error": Optional[str]
        }
    """
    try:
        # Валидация обязательных полей
        required_fields = ["first_name", "last_name", "telegram_tag"]
        for field in required_fields:
            if not admin_data.get(field):
                return {
                    "success": False,
                    "admin": None,
                    "error": f"Поле '{field}' обязательно для заполнения"
                }
        
        # Загружаем существующих админов
        if ADMINS_FILE.exists():
            with open(ADMINS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                admins = data.get("admins", [])
        else:
            admins = []
        
        # Проверяем, не существует ли уже админ с таким telegram_tag
        telegram_tag = admin_data["telegram_tag"].lstrip("@")
        for admin in admins:
            if admin.get("telegram_tag", "").lstrip("@") == telegram_tag:
                return {
                    "success": False,
                    "admin": None,
                    "error": f"Администратор с telegram_tag '@{telegram_tag}' уже существует"
                }
        
        # Генерируем уникальный ID (timestamp в миллисекундах)
        admin_id = int(datetime.now().timestamp() * 1000)
        
        # Формируем данные нового администратора
        new_admin = {
            "id": admin_id,
            "first_name": admin_data["first_name"],
            "last_name": admin_data["last_name"],
            "full_name": f"{admin_data['first_name']} {admin_data['last_name']}".strip(),
            "email": admin_data.get("email"),
            "phone": admin_data.get("phone"),
            "vk_id": admin_data.get("vk_id"),
            "telegram_id": admin_data.get("telegram_id"),
            "telegram_tag": telegram_tag,
            "clans_mentor": [],
            "courses": []
        }
        
        # Добавляем нового админа
        admins.append(new_admin)
        
        # Сохраняем в файл
        result = {
            "export_date": datetime.now().isoformat(),
            "total_unique_admins": len(admins),
            "admins": admins
        }
        
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(ADMINS_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Очищаем кэш загрузчика данных
        from src.services.data_loader import load_json
        load_json.cache_clear()
        
        return {
            "success": True,
            "admin": new_admin,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "admin": None,
            "error": str(e)
        }
