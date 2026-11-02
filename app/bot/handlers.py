import io
import logging
import re
import time
from typing import Optional
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from app.config import get_settings
from app.ai.chat_service import ChatService
from app.ai.image_service import ImageService, clean_prompt

logger = logging.getLogger(__name__)

settings = get_settings()
chat_service = ChatService(settings=settings)
image_service = ImageService(settings=settings)
BOT_START_TIME = time.time()


def detect_image_prompt(text: str) -> Optional[str]:
    """
    Tự động phát hiện nếu người dùng muốn vẽ ảnh mà không gõ /image.
    Ví dụ: 'tạo ảnh con mèo', 'vẽ một chú cún', 'vẽ tranh hoàng hôn', 'draw a cat'.
    """
    text_clean = text.strip()
    patterns = [
        r"^(?:hãy\s+)?(?:tạo|vẽ|sinh|generate|draw)\s+(?:cho\s+(?:mình|em|anh|tôi)\s+)?(?:bức\s+)?(?:ảnh|tranh|hình|image|picture)?\s*(?:về|với)?\s*(.+)$",
        r"^(?:tạo\s+ảnh|vẽ\s+ảnh|vẽ\s+tranh|vẽ\s+hình)\s*[:\s]\s*(.+)$",
        r"^(?:vẽ|draw)\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, text_clean, re.IGNORECASE)
        if match:
            prompt = match.group(1).strip()
            if len(prompt) >= 2:
                return prompt
    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name if update.effective_user else "bạn"
    text = (
        f"🌸 **Chào {user_name}! Mình là Airi Sensei (@AiriSenseiBot)** 🌸\n\n"
        "Rất vui được đồng hành cùng bạn! Mình có 2 tính năng chính:\n\n"
        "💬 **1. Hỏi đáp thông minh:** Bạn chỉ cần nhắn bất kỳ câu hỏi nào, mình sẽ giải đáp chu đáo.\n"
        "🎨 **2. Tạo ảnh nghệ thuật:** Dùng lệnh `/image <mô tả>` hoặc nhắn tự nhiên *'vẽ một chú mèo...'* để mình vẽ tranh cho bạn.\n\n"
        "📌 **Các lệnh hữu ích:**\n"
        "• `/help` - Xem hướng dẫn chi tiết\n"
        "• `/image <mô tả>` - Vẽ ảnh bằng AI\n"
        "• `/models` - Xem danh sách model AI & cơ chế Fallback\n"
        "• `/status` - Xem trạng thái hệ thống & Uptime 24/7\n"
        "• `/clear` - Làm mới ngữ cảnh trò chuyện\n\n"
        "Hãy thử đặt cho mình một câu hỏi hoặc bảo mình vẽ một bức tranh nhé! ✨"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📚 **HƯỚNG DẪN SỬ DỤNG AIRI SENSEI**\n\n"
        "🔹 **Trò chuyện & Hỏi đáp:**\n"
        "Chỉ cần gõ tin nhắn trực tiếp gửi cho bot. Ví dụ:\n"
        "• *'Giải thích sự khác nhau giữa Webhook và Polling?'*\n"
        "• *'Viết giúp mình hàm Python đảo ngược chuỗi.'*\n"
        "• *'Làm thế nào để ngủ ngon hơn mỗi tối?'*\n\n"
        "🔹 **Vẽ tranh AI:**\n"
        "Cách 1: Gõ lệnh `/image <mô tả>` (ví dụ: `/image phi hành gia anime`)\n"
        "Cách 2: Nhắn tự nhiên: *'vẽ con mèo'* hoặc *'tạo ảnh hoàng hôn trên biển 4k'*\n\n"
        "🔹 **Các lệnh quản trị:**\n"
        "• `/clear`: Xóa lịch sử nhớ để bắt đầu cuộc trò chuyện mới\n"
        "• `/models`: Xem danh sách các AI model đang kích hoạt\n"
        "• `/status`: Kiểm tra độ trễ mạng và Uptime của server"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fallback_list = ", ".join(settings.fallback_models_list)
    text = (
        "🤖 **CẤU HÌNH AI MODELS & CƠ CHẾ CASCADING FALLBACK**\n\n"
        f"🥇 **Model chính (Primary):** `{settings.AI_PRIMARY_MODEL}`\n"
        f"🥈 **Các model dự phòng (Fallbacks):** `{fallback_list}`\n"
        f"🌸 **Free Fallback:** `Airi-Flash` (Pollinations AI Free Engine)\n"
        f"🎨 **Engine sinh ảnh:** `{settings.IMAGE_MODEL}` (dự phòng: `{settings.IMAGE_FALLBACK_MODEL}`)\n"
        f"🌐 **AI Gateway:** `{settings.AI_BASE_URL}`\n\n"
        "💡 *Cơ chế hoạt động:* Bot tự động luân chuyển model trong 0.2s khi gặp lỗi quota hoặc quá tải!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uptime_sec = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    text = (
        "⚡ **TRẠNG THÁI HỆ THỐNG AIRI SENSEI**\n\n"
        f"🟢 **Trạng thái:** Online 24/7 (Render Web Service)\n"
        f"⏱️ **Thời gian hoạt động (Uptime):** {uptime_str}\n"
        f"🧠 **AI Engine:** `{settings.AI_PRIMARY_MODEL}` + Cascading Fallback\n"
        f"🎨 **Image Engine:** `{settings.IMAGE_MODEL}` (Flux 1024x1024)\n"
        f"🌐 **HTTP Health Server:** Port `{settings.PORT}` OK"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_service.clear_history(user_id)
    await update.message.reply_text("🧹 Mình đã làm mới bộ nhớ trò chuyện rồi! Chúng ta bắt đầu chủ đề mới nhé! ✨")


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "🎨 Bạn hãy nhập mô tả tranh muốn vẽ nhé!\n\n"
            "👉 *Ví dụ:* `/image một chú mèo phi hành gia bay ngoài vũ trụ phong cách anime 4k`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    prompt = " ".join(context.args).strip()
    await _execute_image_generation(update, prompt)


async def _execute_image_generation(update: Update, prompt: str) -> None:
    cleaned = clean_prompt(prompt)
    status_msg = await update.message.reply_text("🎨 *Airi đang vẽ tranh cho bạn, đợi xíu nhé...*", parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_chat_action(ChatAction.UPLOAD_PHOTO)

    try:
        image_bytes, model_used = await image_service.generate_image(cleaned)
        await status_msg.delete()
        caption = f"🎨 **Tranh của bạn:**\n_{cleaned}_\n\n*(Model: {model_used})*"
        await update.message.reply_photo(
            photo=io.BytesIO(image_bytes),
            caption=caption[:1024],
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error("Error generating image: %s", e)
        await status_msg.edit_text(f"❌ Ôi, không vẽ được ảnh rồi: {e}\nBạn hãy thử lại với mô tả khác nhé!")


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    if not user_message:
        return

    # 1. Kiểm tra nếu người dùng nói ý định vẽ ảnh (ví dụ: 'tạo ảnh con mèo', 'vẽ con mèo')
    detected_prompt = detect_image_prompt(user_message)
    if detected_prompt:
        logger.info("Detected image generation intent: '%s'", detected_prompt)
        await _execute_image_generation(update, detected_prompt)
        return

    # 2. Xử lý câu hỏi thông thường qua AI Chat
    user_id = update.effective_user.id
    await update.message.reply_chat_action(ChatAction.TYPING)

    try:
        reply, model_used = await chat_service.ask(user_id, user_message)
        footer = f"\n\n_— Airi Sensei ({model_used})_"
        full_reply = reply + footer
        try:
            await update.message.reply_text(full_reply, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(full_reply)
    except Exception as e:
        logger.error("Error in text handler: %s", e)
        await update.message.reply_text(f"Dạ có lỗi nhỏ xảy ra: {e}. Bạn hỏi lại nhé!")
