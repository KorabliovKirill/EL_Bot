"""
Сервис для обновления домашних заданий конкретных кланов через API
"""
import json
import os
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests
from urllib.parse import quote

from src.config.settings import DATA_DIR, BASE_DIR
from dotenv import load_dotenv

load_dotenv()

# Конфигурация API
API_BASE_URL = os.getenv("BASE_URL")
LOGIN_URL = f"{API_BASE_URL}/login"
DELAY_BASE = float(os.getenv("DELAY_BASE", 4.5))
DELAY_JITTER = float(os.getenv("DELAY_JITTER", 1.8))

HOMEWORKS_FILE = DATA_DIR / "homeworks.json"


class HomeworkUpdateError(Exception):
    """Ошибка при обновлении домашних заданий"""
    pass


def login(email: str, password: str) -> str:
    """Авторизация и получение токена"""
    try:
        resp = requests.post(
            LOGIN_URL,
            json={"email": email, "password": password},
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except Exception as e:
        raise HomeworkUpdateError(f"Ошибка авторизации: {e}")


def get_clan_homeworks_page(token: str, clan_id: int, page: int = 1) -> tuple[list, dict]:
    """Получение одной страницы домашних заданий клана"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "page": page,
        "filter": "Ожидает проверки",
        "sort": "delivery_desc",
        "lesson_id": "",
    }

    url = f"{API_BASE_URL}/clan/{clan_id}/homeworks"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        
        if resp.status_code == 429:
            time.sleep(60)
            return get_clan_homeworks_page(token, clan_id, page)

        resp.raise_for_status()
        data = resp.json()
        return data.get("data", []), data.get("meta", {})

    except Exception as e:
        raise HomeworkUpdateError(f"Ошибка загрузки домашек клана {clan_id}: {e}")


def add_clan_context(homework: dict, clan_id: int):
    """Добавляет clan_id к домашке"""
    homework["clan_id"] = clan_id


def extract_unique_clan_ids() -> list[int]:
    """Извлекает все уникальные ID кланов из файла наставников"""
    mentors_path = DATA_DIR / "mentors.json"
    
    if not mentors_path.exists():
        raise HomeworkUpdateError(f"Файл наставников не найден: {mentors_path}")
    
    with open(mentors_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    clan_ids = set()
    for mentor in data.get("mentors", []):
        for clan in mentor.get("clans_mentor", []):
            if cid := clan.get("id"):
                clan_ids.add(cid)
    
    return sorted(clan_ids)


async def update_all_homeworks() -> dict:
    """
    Обновляет все домашние задания по всем кланам из базы наставников
    
    Returns:
        dict с информацией об обновлении:
        {
            "success": bool,
            "total_clans": int,
            "total_homeworks": int,
            "error": Optional[str]
        }
    """
    email = os.getenv("API_EMAIL")
    password = os.getenv("API_PASSWORD")
    
    if not email or not password:
        return {
            "success": False,
            "total_clans": 0,
            "total_homeworks": 0,
            "error": "API_EMAIL или API_PASSWORD не настроены"
        }
    
    try:
        # Получаем все кланы из базы наставников
        clan_ids = extract_unique_clan_ids()
        
        if not clan_ids:
            return {
                "success": False,
                "total_clans": 0,
                "total_homeworks": 0,
                "error": "Нет кланов в базе наставников"
            }
        
        # Авторизация
        token = login(email, password)
        
        # Загружаем домашки для всех кланов
        all_homeworks = []
        
        for clan_id in clan_ids:
            page = 1
            
            while True:
                homeworks, meta = get_clan_homeworks_page(token, clan_id, page)
                
                if not homeworks:
                    break
                
                for hw in homeworks:
                    add_clan_context(hw, clan_id)
                
                all_homeworks.extend(homeworks)
                
                last_page = meta.get("last_page", 1)
                
                if page >= last_page:
                    break
                
                page += 1
                # Случайная задержка
                sleep_time = DELAY_BASE + random.uniform(-DELAY_JITTER, DELAY_JITTER)
                time.sleep(max(1.0, sleep_time))
        
        # Сохраняем результат
        result = {
            "exported_at": datetime.now().isoformat(),
            "total_pending": len(all_homeworks),
            "clans_processed": len(clan_ids),
            "homeworks": all_homeworks
        }
        
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(HOMEWORKS_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Очищаем кэш загрузчика данных
        from src.services.data_loader import load_json
        load_json.cache_clear()
        
        return {
            "success": True,
            "total_clans": len(clan_ids),
            "total_homeworks": len(all_homeworks),
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "total_clans": 0,
            "total_homeworks": 0,
            "error": str(e)
        }


async def update_homeworks_for_clans(clan_ids: list[int]) -> dict:
    """
    Обновляет домашние задания для указанных кланов
    
    Args:
        clan_ids: список ID кланов для обновления
        
    Returns:
        dict с информацией об обновлении:
        {
            "success": bool,
            "updated_clans": int,
            "total_homeworks": int,
            "error": Optional[str]
        }
    """
    if not clan_ids:
        return {
            "success": False,
            "updated_clans": 0,
            "total_homeworks": 0,
            "error": "Нет кланов для обновления"
        }
    
    email = os.getenv("API_EMAIL")
    password = os.getenv("API_PASSWORD")
    
    if not email or not password:
        return {
            "success": False,
            "updated_clans": 0,
            "total_homeworks": 0,
            "error": "API_EMAIL или API_PASSWORD не настроены"
        }
    
    try:
        # Авторизация
        token = login(email, password)
        
        # Загружаем существующие домашки
        if HOMEWORKS_FILE.exists():
            with open(HOMEWORKS_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_homeworks = existing_data.get("homeworks", [])
        else:
            existing_homeworks = []
        
        # Удаляем старые домашки обновляемых кланов
        other_clans_homeworks = [
            hw for hw in existing_homeworks
            if hw.get("clan_id") not in clan_ids
        ]
        
        # Загружаем новые домашки для указанных кланов
        new_homeworks = []
        
        for clan_id in clan_ids:
            page = 1
            clan_count = 0
            
            while True:
                homeworks, meta = get_clan_homeworks_page(token, clan_id, page)
                
                if not homeworks:
                    break
                
                for hw in homeworks:
                    add_clan_context(hw, clan_id)
                
                new_homeworks.extend(homeworks)
                clan_count += len(homeworks)
                
                last_page = meta.get("last_page", 1)
                
                if page >= last_page:
                    break
                
                page += 1
                # Случайная задержка
                sleep_time = DELAY_BASE + random.uniform(-DELAY_JITTER, DELAY_JITTER)
                time.sleep(max(1.0, sleep_time))
        
        # Объединяем домашки: старые (других кланов) + новые (обновленных кланов)
        all_homeworks = other_clans_homeworks + new_homeworks
        
        # Сохраняем результат
        result = {
            "exported_at": datetime.now().isoformat(),
            "total_pending": len(all_homeworks),
            "homeworks": all_homeworks
        }
        
        with open(HOMEWORKS_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Очищаем кэш загрузчика данных
        from src.services.data_loader import load_json
        load_json.cache_clear()
        
        return {
            "success": True,
            "updated_clans": len(clan_ids),
            "total_homeworks": len(new_homeworks),
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "updated_clans": 0,
            "total_homeworks": 0,
            "error": str(e)
        }
