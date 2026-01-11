# src/utils/telegram.py
from aiogram.types import Message

TELEGRAM_LIMIT = 4096
PREFIX_TEMPLATE = "Часть {i}/{total}\n\n"


async def send_split_message(
    message: Message,
    text: str,
    **kwargs
):
    """
    Надёжно отправляет длинный текст, гарантируя,
    что ни одно сообщение не превысит лимит Telegram.
    """

    # Быстрый путь
    if len(text) <= TELEGRAM_LIMIT:
        await message.answer(text, **kwargs)
        return

    lines = text.splitlines(keepends=True)
    parts: list[str] = []
    current = ""

    for line in lines:
        if len(current) + len(line) > TELEGRAM_LIMIT:
            parts.append(current.rstrip())
            current = line
        else:
            current += line

    if current:
        parts.append(current.rstrip())

    total = len(parts)

    for i, part in enumerate(parts, start=1):
        prefix = PREFIX_TEMPLATE.format(i=i, total=total) if total > 1 else ""
        max_len = TELEGRAM_LIMIT - len(prefix)

        # 🔐 финальная защита
        safe_part = part[:max_len]

        await message.answer(prefix + safe_part, **kwargs)
