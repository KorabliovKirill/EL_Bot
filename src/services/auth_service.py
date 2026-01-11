from src.services.data_loader import get_mentors, get_admins


def is_authorized(username: str | None) -> bool:
    if not username:
        return False
    
    username = username.lstrip("@")
    
    mentors = get_mentors()
    admins = get_admins()
    
    all_users = mentors + admins
    
    return any(
        user.get("telegram_tag", "").lstrip("@") == username
        for user in all_users
    )


def get_user_clan_ids(username: str | None) -> list[int]:
    if not username:
        return []
    
    username = username.lstrip("@")
    
    mentors = get_mentors()
    admins = get_admins()
    
    for user in mentors + admins:
        if user.get("telegram_tag", "").lstrip("@") == username:
            return [clan["id"] for clan in user.get("clans_mentor", [])]
    
    return []


def get_mentor_telegram_ids_by_clan(clan_id: int) -> list[str]:
    mentors = get_mentors()
    ids = []
    
    for mentor in mentors:
        if any(clan["id"] == clan_id for clan in mentor.get("clans_mentor", [])):
            tg_id = mentor.get("telegram_id")
            if tg_id:
                ids.append(str(tg_id))
    
    return ids


def is_admin(username: str | None) -> bool:
    """
    Проверяет, является ли пользователь администратором
    
    Args:
        username: Telegram username пользователя
        
    Returns:
        True если пользователь является администратором, иначе False
    """
    if not username:
        return False
    
    username = username.lstrip("@")
    admins = get_admins()
    
    return any(
        admin.get("telegram_tag", "").lstrip("@") == username
        for admin in admins
    )


def get_user_info(username: str | None) -> dict | None:
    """
    Получает полную информацию о пользователе (наставник или админ)
    
    Args:
        username: Telegram username пользователя
        
    Returns:
        Словарь с информацией о пользователе или None если не найден
    """
    if not username:
        return None
    
    username = username.lstrip("@")
    
    mentors = get_mentors()
    admins = get_admins()
    
    # Ищем сначала в наставниках
    for mentor in mentors:
        if mentor.get("telegram_tag", "").lstrip("@") == username:
            return {**mentor, "role": "mentor"}
    
    # Затем в админах
    for admin in admins:
        if admin.get("telegram_tag", "").lstrip("@") == username:
            return {**admin, "role": "admin"}
    
    return None