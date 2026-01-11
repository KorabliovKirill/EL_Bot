from typing import TypedDict, Literal, Any


class MentorDict(TypedDict):
    id: int
    first_name: str
    last_name: str
    full_name: str
    telegram_tag: str | None
    telegram_id: str | None
    clans_mentor: list[ClanDict]


class AdminDict(TypedDict):
    id: int
    first_name: str
    last_name: str
    full_name: str
    telegram_tag: str | None
    telegram_id: str | None
    clans_mentor: list[ClanDict]


class ClanDict(TypedDict):
    id: int
    name: str
    slogan: str
    target: int | None
    class_: int   # class — зарезервированное слово, поэтому class_
    max_students_count: int


class HomeworkDict(TypedDict):
    id: int
    delivery_date: str
    status: Literal["Ожидает проверки", "Проверено", "..."]  # можно расширять
    clan_id: int
    user: dict  # StudentDict в будущем
    homework: dict


HomeworkStatus = Literal["overdue", "expiring_soon", "in_time", None]