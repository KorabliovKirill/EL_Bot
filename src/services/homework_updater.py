"""
Сервис для обновления домашних заданий конкретных кланов через API
"""
import json
import os
import asyncio
import random
from pathlib import Path
from datetime import datetime
from typing import Optional
import aiohttp
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


async def login(email: str, password: str, session: aiohttp.ClientSession) -> str:
    """Авторизация и получение токена"""
    try:
        async with session.post(
            LOGIN_URL,
            json={"email": email, "password": password},
            timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["access_token"]
    except Exception as e:
        raise HomeworkUpdateError(f"Ошибка авторизации: {e}")


async def get_clan_homeworks_page(
    token: str, 
    clan_id: int, 
    page: int,
    session: aiohttp.ClientSession
) -> tuple[list, dict]:
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
        async with session.get(
            url, 
            headers=headers, 
            params=params, 
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 429:
                await asyncio.sleep(60)
                return await get_clan_homeworks_page(token, clan_id, page, session)

            resp.raise_for_status()
            data = await resp.json()
            return data.get("data", []), data.get("meta", {})

    except Exception as e:
        raise HomeworkUpdateError(f"Ошибка загрузки домашек клана {clan_id}: {e}")


def add_clan_context(homework: dict, clan_id: int):
    """Добавляет clan_id к домашке"""
    homework["clan_id"] = clan_id


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
        # Создаем сессию для всех запросов
        async with aiohttp.ClientSession() as session:
            # Авторизация
            token = await login(email, password, session)
            
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
                    homeworks, meta = await get_clan_homeworks_page(
                        token, clan_id, page, session
                    )
                    
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
                    await asyncio.sleep(max(1.0, sleep_time))
        
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
