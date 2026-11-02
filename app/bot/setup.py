import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.config import Settings, get_settings
from app.bot.handlers import (
    start_command,
    auth_command,
    help_command,
    models_command,
    status_command,
    clear_command,
    image_command,
    text_message_handler,
)

logger = logging.getLogger(__name__)


def build_bot_app(settings: Settings = None) -> Application:
    current_settings = settings or get_settings()

    app = Application.builder().token(current_settings.BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("auth", auth_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("models", models_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler(["image", "taoanh"], image_command))

    # General text messages (Q&A)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    logger.info("Registered all bot command and message handlers")
    return app
