from pathlib import Path
import os
import time
import json
import requests
from datetime import datetime
import random
from urllib.parse import quote

from dotenv import load_dotenv

# -------------------------------------------------
# Загрузка конфигурации
# -------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

API_BASE_URL = os.getenv("BASE_URL")
if not API_BASE_URL:
    raise RuntimeError("BASE_URL не задан в .env")

LOGIN_URL = f"{API_BASE_URL}/login"

DELAY_BASE = float(os.getenv("DELAY_BASE", 4.5))
DELAY_JITTER = float(os.getenv("DELAY_JITTER", 1.8))
PER_PAGE = int(os.getenv("PER_PAGE", 50))

OUTPUT_DIR = ROOT_DIR / os.getenv("OUTPUT_DIR", "data")
HOMEWORKS_FILE = OUTPUT_DIR / os.getenv("OUTPUT_FILE_HOMEWORKS", "homeworks.json")

PENDING_FILTER = quote("Ожидает проверки")

# -------------------------------------------------
# API-функции
# -------------------------------------------------
def login(email: str, password: str) -> str:
    """Авторизация и получение токена"""
    resp = requests.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


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
            print("  429 Too Many Requests → ждём 60 секунд...")
            time.sleep(60)
            return get_clan_homeworks_page(token, clan_id, page)

        resp.raise_for_status()
        data = resp.json()
        return data.get("data", []), data.get("meta", {})

    except (requests.Timeout, requests.ConnectionError) as e:
        print(f"  Ошибка соединения (клан {clan_id}, стр {page}): {e}")
        return [], {}
    except requests.HTTPError as e:
        print(f"  HTTP {resp.status_code} (клан {clan_id}, стр {page}): {resp.text[:300]}")
        return [], {}
    except Exception as e:
        print(f"  Неожиданная ошибка (клан {clan_id}, стр {page}): {e}")
        return [], {}


# -------------------------------------------------
# Утилиты
# -------------------------------------------------
def extract_unique_clan_ids(mentors_path: Path) -> list[int]:
    if not mentors_path.exists():
        raise FileNotFoundError(f"Файл не найден: {mentors_path}")

    with open(mentors_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    clan_ids = set()
    for mentor in data.get("mentors", []):
        for clan in mentor.get("clans_mentor", []):
            if cid := clan.get("id"):
                clan_ids.add(cid)
    return sorted(clan_ids)


def add_clan_context(homework: dict, clan_id: int):
    homework["clan_id"] = clan_id


# -------------------------------------------------
# Основная логика
# -------------------------------------------------
def main():
    print("Выгрузка ДЗ, ожидающих проверки — ЕГЭLand\n")

    email = os.getenv("API_EMAIL")
    password = os.getenv("API_PASSWORD")
    if not email or not password:
        raise RuntimeError("API_EMAIL или API_PASSWORD не заданы в .env")

    print("Авторизация... ", end="")
    token = login(email, password)
    print("OK")

    mentors_path = OUTPUT_DIR / os.getenv("OUTPUT_FILE_MENTORS", "mentors.json")
    print("Чтение списка кланов... ", end="")
    clan_ids = extract_unique_clan_ids(mentors_path)
    print(f"{len(clan_ids)} уникальных кланов")

    all_homeworks = []
    processed = 0

    for clan_id in clan_ids:
        processed += 1
        print(f"\n→ Клан {clan_id}  ({processed}/{len(clan_ids)})")

        page = 1
        clan_count = 0

        while True:
            print(f"  стр {page}... ", end="", flush=True)
            homeworks, meta = get_clan_homeworks_page(token, clan_id, page)

            if not homeworks:
                print("пусто")
                break

            for hw in homeworks:
                add_clan_context(hw, clan_id)

            all_homeworks.extend(homeworks)
            clan_count += len(homeworks)

            last_page = meta.get("last_page", 1)
            print(f"+{len(homeworks)}  (по клану: {clan_count} | всего: {len(all_homeworks)})")

            if page >= last_page:
                break

            page += 1
            # Случайная человеческая задержка
            sleep_time = DELAY_BASE + random.uniform(-DELAY_JITTER, DELAY_JITTER)
            time.sleep(max(1.0, sleep_time))

    # Сохранение результата
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "exported_at": datetime.now().isoformat(),
        "total_pending": len(all_homeworks),
        "clans_processed": len(clan_ids),
        "homeworks": all_homeworks
    }

    with open(HOMEWORKS_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nГотово!")
    print(f"Всего заданий ожидающих проверки: {len(all_homeworks):,}")
    print(f"Сохранено → {HOMEWORKS_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nОстановлено пользователем")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")