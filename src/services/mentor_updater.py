"""
Сервис для обновления базы наставников через API
"""
import json
import os
import time
from pathlib import Path
from datetime import datetime
import requests
from dotenv import load_dotenv

from src.config.settings import DATA_DIR

load_dotenv()

# Конфигурация API
BASE_URL = os.getenv("BASE_URL")
LOGIN_URL = f"{BASE_URL}/login"
MENTORS_URL = f"{BASE_URL}/mentors"

PER_PAGE = int(os.getenv("PER_PAGE", 200))
DELAY = float(os.getenv("DELAY", 1.0))

MENTORS_FILE = DATA_DIR / "mentors.json"


class MentorUpdateError(Exception):
    """Ошибка при обновлении базы наставников"""
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
        raise MentorUpdateError(f"Ошибка авторизации: {e}")


def get_mentors_page(token: str, page: int) -> dict:
    """Получение одной страницы наставников"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "page": page,
        "per_page": PER_PAGE,
    }

    try:
        resp = requests.get(
            MENTORS_URL,
            headers=headers,
            params=params,
            timeout=15
        )

        if resp.status_code == 429:
            time.sleep(25)
            return get_mentors_page(token, page)

        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise MentorUpdateError(f"Ошибка загрузки страницы {page}: {e}")


def clean_mentor(mentor: dict) -> dict:
    """Приводим данные наставника к удобному виду"""
    return {
        "id": mentor.get("id"),
        "first_name": mentor.get("first_name"),
        "last_name": mentor.get("last_name"),
        "full_name": f"{mentor.get('first_name', '')} {mentor.get('last_name', '')}".strip(),
        "email": mentor.get("email"),
        "phone": mentor.get("phone"),
        "vk_id": mentor.get("vk_id"),
        "telegram_id": mentor.get("telegram_id"),
        "telegram_tag": mentor.get("telegram_tag"),
        "clans_mentor": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "slogan": c.get("slogan"),
                "target": c.get("target"),
                "class": c.get("class"),
                "max_students_count": c.get("max_students_count"),
            }
            for c in mentor.get("clansMentor", [])
        ],
        "courses": [
            {
                "id": course.get("id"),
                "name": course.get("name"),
                "subject": course.get("subject", {}).get("name")
                if course.get("subject") else None,
            }
            for course in mentor.get("courses", [])
        ],
    }


async def update_all_mentors() -> dict:
    """
    Обновляет всю базу наставников через API
    
    Returns:
        dict с информацией об обновлении:
        {
            "success": bool,
            "total_mentors": int,
            "filtered_mentors": int,
            "error": Optional[str]
        }
    """
    email = os.getenv("API_EMAIL")
    password = os.getenv("API_PASSWORD")
    
    if not email or not password:
        return {
            "success": False,
            "total_mentors": 0,
            "filtered_mentors": 0,
            "error": "API_EMAIL или API_PASSWORD не настроены"
        }
    
    try:
        # Авторизация
        token = login(email, password)
        
        all_mentors = []
        seen_ids = set()
        page = 1
        last_meta = {}
        
        # Загружаем все страницы
        while True:
            data = get_mentors_page(token, page)
            mentors = data.get("data", [])
            last_meta = data.get("meta", {})
            
            if not mentors:
                break
            
            for mentor in mentors:
                mid = mentor.get("id")
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    all_mentors.append(clean_mentor(mentor))
            
            last_page = last_meta.get("last_page", page)
            
            if page >= last_page:
                break
            
            page += 1
            time.sleep(DELAY)
        
        # Фильтруем наставников (оставляем только с telegram_tag и кланами)
        filtered_mentors = [
            m for m in all_mentors
            if m.get("telegram_tag") not in (None, "") and m.get("clans_mentor")
        ]
        
        # Сохраняем результат
        result = {
            "export_date": datetime.now().isoformat(),
            "total_unique_mentors": len(filtered_mentors),
            "total_from_meta": last_meta.get("total"),
            "per_page": PER_PAGE,
            "mentors": filtered_mentors,
        }
        
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(MENTORS_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Очищаем кэш загрузчика данных
        from src.services.data_loader import load_json
        load_json.cache_clear()
        
        return {
            "success": True,
            "total_mentors": len(all_mentors),
            "filtered_mentors": len(filtered_mentors),
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "total_mentors": 0,
            "filtered_mentors": 0,
            "error": str(e)
        }
