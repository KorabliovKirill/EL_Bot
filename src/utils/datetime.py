from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def parse_delivery_date(date_str: str) -> datetime:
    """Парсит строку вида 2025-09-21T22:02:06.000000Z → aware datetime в UTC"""
    if date_str.endswith("Z"):
        date_str = date_str[:-1]
    dt = datetime.fromisoformat(date_str)
    return dt.replace(tzinfo=UTC)


def now_utc() -> datetime:
    """Всегда возвращает текущий момент в UTC как aware datetime"""
    return datetime.now(UTC)


def hours_since_delivery(delivery: datetime, now: datetime | None = None) -> float:
    if now is None:
        now = now_utc()
    # Убеждаемся, что обе даты aware
    if delivery.tzinfo is None:
        delivery = delivery.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return (now - delivery).total_seconds() / 3600


def hours_left_to_deadline(delivery: datetime, now: datetime | None = None) -> float:
    if now is None:
        now = now_utc()
    deadline = delivery + timedelta(hours=72)
    if delivery.tzinfo is None:
        delivery = delivery.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return max(0, (deadline - now).total_seconds() / 3600)