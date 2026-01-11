# src/utils/telegram.py
from aiogram.types import Message

MAX_MESSAGE_LENGTH = 4090  # запас на форматирование и подписи


async def send_split_message(
    message: Message,
    text: str,
    chunk_separator: str = "\n\n",
    **kwargs
):
    """
    Отправляет длинный текст, разбивая его на части ≤ 4096 символов
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        await message.answer(text, **kwargs)
        return

    parts = []
    current = ""

    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > MAX_MESSAGE_LENGTH:
            parts.append(current.rstrip())
            current = line
        else:
            current += line

    if current:
        parts.append(current.rstrip())

    for i, part in enumerate(parts, 1):
        prefix = f"Часть {i}/{len(parts)}\n\n" if len(parts) > 1 else ""
        await message.answer(prefix + part, **kwargs)