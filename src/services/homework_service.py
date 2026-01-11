from collections import defaultdict
from datetime import datetime
from src.services.data_loader import get_homeworks
from src.services.auth_service import get_user_clan_ids
from src.utils.datetime import (
    parse_delivery_date,
    hours_since_delivery,
    hours_left_to_deadline,
    now_utc
)


def get_relevant_homeworks(username: str | None) -> list[dict]:
    if not username:
        return []
    
    clan_ids = get_user_clan_ids(username)
    if not clan_ids:
        # Админы без кланов могут видеть всё (можно изменить логику)
        return [hw for hw in get_homeworks() if hw.get("status") == "Ожидает проверки"]
    
    return [
        hw for hw in get_homeworks()
        if hw.get("clan_id") in clan_ids and hw.get("status") == "Ожидает проверки"
    ]


def classify_homework(hw: dict, now: datetime | None = None) -> str | None:
    if hw.get("status") != "Ожидает проверки":
        return None
    
    if now is None:
        now = now_utc()
    
    delivery = parse_delivery_date(hw["delivery_date"])
    hours_passed = hours_since_delivery(delivery, now)
    
    if hours_passed > 72:
        return "overdue"
    if hours_left_to_deadline(delivery, now) <= 24:
        return "expiring_soon"
    return "in_time"


def get_homeworks_info(username: str | None) -> tuple[str, str]:
    now = now_utc()
    hws = get_relevant_homeworks(username)
    
    if not hws:
        return "У вас нет домашних заданий на проверке.", ""

    by_clan = defaultdict(list)
    for hw in hws:
        by_clan[hw["clan_id"]].append(hw)
    
    total_lines = ["📊 Домашние задания на проверке:"]
    for clan_id, clan_hws in sorted(by_clan.items()):
        total_lines.append(f"Клан {clan_id}: {len(clan_hws)}")
    
    total_text = "\n".join(total_lines)
    
    overdue = sum(1 for hw in hws if classify_homework(hw, now) == "overdue")
    pending = len(hws) - overdue
    
    status_lines = [
        "Статус:",
        f"Просрочено (>72ч): {overdue}",
        f"В срок: {pending}"
    ]
    
    return total_text, "\n".join(status_lines)


def get_expiring_homeworks_text(username: str | None) -> str:
    now = now_utc()                         # ← исправлено
    hws = get_relevant_homeworks(username)
    
    expiring = [
        hw for hw in hws
        if classify_homework(hw, now) == "expiring_soon"
    ]
    
    if not expiring:
        return "На данный момент нет домашних заданий, которые истекают в ближайшие 24 часа."
    
    lines = ["Домашние задания, истекающие в ближайшие 24 часа:"]
    
    for hw in sorted(
        expiring,
        key=lambda x: hours_left_to_deadline(parse_delivery_date(x["delivery_date"]), now)
    ):
        delivery = parse_delivery_date(hw["delivery_date"])
        hours_left = hours_left_to_deadline(delivery, now)
        student = hw["user"]["first_name"].strip() + " " + hw["user"].get("last_name", "").strip()
        
        # Используем lesson.topic вместо type.name
        lesson = hw["homework"].get("lesson", {})
        task_name = lesson.get("topic", hw["homework"]["type"]["name"])  # fallback на type.name
        
        lines.append(
            f"• {student.strip() or '??'} — {task_name} "
            f"(клан {hw['clan_id']}, осталось ~{int(hours_left)} ч)"
        )
    
    return "\n".join(lines)