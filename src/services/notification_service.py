from datetime import datetime, timedelta
from src.services.data_loader import get_homeworks
from src.services.auth_service import get_mentor_telegram_ids_by_clan
from src.utils.datetime import parse_delivery_date, hours_left_to_deadline


def get_pending_notifications() -> list[tuple[str, str]]:
    now = datetime.now()
    notifications = []
    
    for hw in get_homeworks():
        if hw.get("status") != "Ожидает проверки":
            continue
            
        delivery = parse_delivery_date(hw["delivery_date"])
        hours_left = hours_left_to_deadline(delivery, now)
        
        # Окна отправки с небольшой гистерезисом, чтобы не спамить
        if 23.7 <= hours_left <= 24.3:
            level = 24
        elif 11.7 <= hours_left <= 12.3:
            level = 12
        else:
            continue
            
        clan_id = hw["clan_id"]
        tg_ids = get_mentor_telegram_ids_by_clan(clan_id)
        
        student = (hw["user"]["first_name"] + " " + hw["user"].get("last_name", "")).strip() or "??"
        
        # Используем lesson.topic вместо type.name
        lesson = hw["homework"].get("lesson", {})
        task = lesson.get("topic", hw["homework"]["type"]["name"])  # fallback на type.name
        
        text = (
            f"⚠️ Напоминание\n"
            f"Осталось ~{level} часов на проверку ДЗ\n"
            f"Ученик: {student}\n"
            f"Задание: {task}\n"
            f"Клан: {clan_id}"
        )
        
        for tg_id in tg_ids:
            notifications.append((tg_id, text))
    
    return notifications