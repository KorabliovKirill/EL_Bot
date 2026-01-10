from pathlib import Path
import os
import time
import json
import requests
from datetime import datetime

from dotenv import load_dotenv

# -------------------------------------------------
# Загрузка .env из корня проекта
# -------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# -------------------------------------------------
# Конфигурация из .env
# -------------------------------------------------
BASE_URL = os.getenv("BASE_URL")
LOGIN_URL = f"{BASE_URL}/login"
MENTORS_URL = f"{BASE_URL}/mentors"

EMAIL = os.getenv("API_EMAIL")
PASSWORD = os.getenv("API_PASSWORD")

PER_PAGE = int(os.getenv("PER_PAGE", 200))
DELAY = float(os.getenv("DELAY", 1.0))

OUTPUT_DIR = ROOT_DIR / os.getenv("OUTPUT_DIR", "data")
OUTPUT_FILE = OUTPUT_DIR / os.getenv("OUTPUT_FILE", "mentors.json")

# -------------------------------------------------
# API
# -------------------------------------------------
def login(email: str, password: str) -> str:
    """Авторизация"""
    resp = requests.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_mentors_page(token: str, page: int) -> dict:
    """Получение одной страницы наставников"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "page": page,
        "per_page": PER_PAGE,
    }

    resp = requests.get(
        MENTORS_URL,
        headers=headers,
        params=params,
        timeout=15
    )

    if resp.status_code == 429:
        print("  429 Too Many Requests → ждём 25 секунд...")
        time.sleep(25)
        return get_mentors_page(token, page)

    resp.raise_for_status()
    return resp.json()

# -------------------------------------------------
# Utils
# -------------------------------------------------
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


def remove_mentors_without_telegram_or_clans(file_path: Path) -> None:
    """
    Удаляет из JSON всех наставников, у которых:
    - telegram_tag == null или пустой
    - clans_mentor пустой список []
    Файл перезаписывается
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mentors = data.get("mentors", [])
    before = len(mentors)

    filtered_mentors = [
        m for m in mentors
        if m.get("telegram_tag") not in (None, "") and m.get("clans_mentor")
    ]

    after = len(filtered_mentors)

    data["mentors"] = filtered_mentors
    data["total_unique_mentors"] = after

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(
        f"\n🧹 Фильтрация наставников:"
        f"\n  Было: {before}"
        f"\n  Осталось: {after}"
        f"\n  Удалено: {before - after}"
    )

# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    print("Выгрузка ВСЕХ наставников ЕГЭLand\n")

    if not EMAIL or not PASSWORD:
        raise RuntimeError("❌ API_EMAIL или API_PASSWORD не заданы в .env")

    print("Авторизация...", end=" ")
    token = login(EMAIL, PASSWORD)
    print("OK")

    all_mentors = []
    seen_ids = set()

    page = 1
    total_found = 0
    last_meta = {}

    print(f"\nЗагрузка страниц по {PER_PAGE} записей\n")

    while True:
        print(f"  Страница {page}...", end=" ", flush=True)

        data = get_mentors_page(token, page)
        mentors = data.get("data", [])
        last_meta = data.get("meta", {})

        if not mentors:
            print("пусто → завершение")
            break

        new_on_page = 0
        for mentor in mentors:
            mid = mentor.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                all_mentors.append(clean_mentor(mentor))
                new_on_page += 1
                total_found += 1

        last_page = last_meta.get("last_page", page)
        total = last_meta.get("total", "??")

        print(f"+{new_on_page} | всего: {total_found} / ~{total}")

        if page >= last_page:
            print("Последняя страница")
            break

        page += 1
        time.sleep(DELAY)

    # -------------------------------------------------
    # Save
    # -------------------------------------------------
    OUTPUT_DIR.mkdir(exist_ok=True)

    result = {
        "export_date": datetime.now().isoformat(),
        "total_unique_mentors": len(all_mentors),
        "total_from_meta": last_meta.get("total"),
        "per_page": PER_PAGE,
        "mentors": all_mentors,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\nГотово!")
    print(f"Уникальных наставников: {len(all_mentors):,}")
    print(f"Файл: {OUTPUT_FILE}")

    # -------------------------------------------------
    # Remove mentors without telegram or clans
    # -------------------------------------------------
    remove_mentors_without_telegram_or_clans(OUTPUT_FILE)


if __name__ == "__main__":
    main()
