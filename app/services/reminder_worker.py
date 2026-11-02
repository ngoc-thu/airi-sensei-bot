import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


async def run_reminder_loop(bot: Bot, memory_service: MemoryService, interval: int = 15):
    """
    Vòng lặp chạy ngầm kiểm tra và bắn tin nhắn nhắc nhở (Scheduled Reminders)
    đến người dùng Telegram đúng giờ đã hẹn.
    """
    logger.info("Airi Reminder Worker started.")
    while True:
        try:
            due_reminders = memory_service.get_due_reminders()
            for r in due_reminders:
                try:
                    text = (
                        f"⏰ **Airi nhắc nhở anh nè:**\n\n"
                        f"_{r['reminder_text']}_\n\n"
                        f"— Airi Sensei 🌸"
                    )
                    await bot.send_message(
                        chat_id=r["user_id"],
                        text=text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    memory_service.mark_reminder_sent(r["id"])
                    logger.info("Successfully delivered reminder #%d to user %s", r["id"], r["user_id"])
                except Exception as e:
                    logger.error("Failed to deliver reminder #%d to user %s: %s", r["id"], r["user_id"], e)
        except Exception as err:
            logger.error("Error in reminder worker loop: %s", err)

        await asyncio.sleep(interval)
