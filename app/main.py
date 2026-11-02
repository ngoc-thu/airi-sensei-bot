import asyncio
import logging
import signal
from aiohttp import web
from app.config import get_settings
from app.bot.setup import build_bot_app
from app.server.web import create_web_app
from app.services.keep_alive import run_keep_alive_loop
from app.services.memory_service import MemoryService
from app.services.reminder_worker import run_reminder_loop


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, level.upper(), logging.INFO)
    )


async def main():
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger = logging.getLogger("app.main")
    logger.info("Initializing Airi Sensei Telegram Bot & HTTP Server...")

    # 1. Build Bot Application
    bot_app = build_bot_app(settings)

    # 2. Build Web Application
    web_app = create_web_app(settings)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.HOST, port=settings.PORT)
    await site.start()
    logger.info("HTTP Server listening on http://%s:%d", settings.HOST, settings.PORT)

    # 3. Start Telegram Bot Polling
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram Bot polling started successfully!")

    # 4. Background tasks: Keep-alive & Reminder Worker
    memory_service = MemoryService()
    reminder_task = asyncio.create_task(run_reminder_loop(bot_app.bot, memory_service))

    keep_alive_task = None
    if settings.KEEP_ALIVE_URL:
        keep_alive_task = asyncio.create_task(run_keep_alive_loop(settings.KEEP_ALIVE_URL))

    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: stop_event.set())
        except NotImplementedError:
            # Signal handling on non-Unix platforms
            pass

    try:
        await stop_event.wait()
    finally:
        logger.info("Shutting down gracefully...")
        if reminder_task:
            reminder_task.cancel()
        if keep_alive_task:
            keep_alive_task.cancel()
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        await runner.cleanup()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
