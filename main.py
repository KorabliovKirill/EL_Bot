import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.bot import bot, dp
from src.services.notification_service import get_pending_notifications


async def send_notifications_job():
    notifications = get_pending_notifications()
    for chat_id, text in notifications:
        try:
            await bot.send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление {chat_id}: {e}")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_notifications_job, "interval", minutes=6)  # Каждые ~6 минут
    scheduler.start()

    logging.info("Бот запущен. Планировщик уведомлений активен.")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())