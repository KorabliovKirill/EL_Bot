from pathlib import Path
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# -------------------------------------------------
# Загрузка .env
# -------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "data"))
OUTPUT_FILE = OUTPUT_DIR / "admins.json"

# -------------------------------------------------
# Функция ввода данных админа
# -------------------------------------------------
def input_admin_data() -> dict:
    print("\nВведите данные администратора:\n")

    first_name = input("Имя: ").strip()
    last_name = input("Фамилия: ").strip()
    email = input("Email: ").strip()
    phone = input("Телефон: ").strip()
    vk_id = input("VK ID (можно оставить пустым): ").strip() or None
    telegram_id = input("Telegram ID (число, можно оставить пустым): ").strip()
    telegram_id = int(telegram_id) if telegram_id else None
    telegram_tag = input("Telegram Tag (можно оставить пустым): ").strip() or None

    # Генерируем уникальный ID для теста (timestamp + случайное число)
    admin_id = int(datetime.now().timestamp() * 1000)

    return {
        "id": admin_id,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}".strip(),
        "email": email,
        "phone": phone,
        "vk_id": vk_id,
        "telegram_id": telegram_id,
        "telegram_tag": telegram_tag,
        "clans_mentor": [],
        "courses": [],
    }

# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Считываем существующих админов
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            admins = data.get("admins", [])
    else:
        admins = []

    while True:
        admin = input_admin_data()
        admins.append(admin)
        print(f"\n✅ Админ '{admin['full_name']}' добавлен!")

        cont = input("\nХотите добавить ещё одного админа? (y/n): ").strip().lower()
        if cont != "y":
            break

    # Сохраняем в файл
    result = {
        "export_date": datetime.now().isoformat(),
        "total_unique_admins": len(admins),
        "admins": admins,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nФайл обновлён: {OUTPUT_FILE}")
    print(f"Всего админов: {len(admins)}")

if __name__ == "__main__":
    main()
