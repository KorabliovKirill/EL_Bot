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