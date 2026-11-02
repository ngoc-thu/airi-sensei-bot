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
from app.services.auth_service import AuthService
from app.agent.agent import AiriAgent

logger = logging.getLogger(__name__)

settings = get_settings()
chat_service = ChatService(settings=settings)
image_service = ImageService(settings=settings)
auth_service = AuthService(settings=settings)
airi_agent = AiriAgent(settings=settings, image_service=image_service)
BOT_START_TIME = time.time()


def detect_image_prompt(text: str) -> Optional[str]:
    """
    Tự động phát hiện nếu người dùng muốn vẽ ảnh mà không gõ /image.
    Ví dụ: 'tạo ảnh con mèo', 'vẽ một chú cún', 'vẽ tranh hoàng hôn', 'draw a cat'.
    """
    text_clean = text.strip()
    patterns = [
        (
            r"^(?:hãy\s+)?(?:tạo|vẽ|sinh|generate|draw)\s+(?:cho\s+(?:mình|em|anh|tôi)\s+)?"
            r"(?:bức\s+)?(?:ảnh|tranh|hình|image|picture)?\s*(?:về|với)?\s*(.+)$"
        ),
        r"^(?:tạo\s+ảnh|vẽ\s+ảnh|vẽ\s+tranh|vẽ\s+hình)\s*[:\s]*\s*(.+)$",
        r"^(?:vẽ|draw)\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, text_clean, re.IGNORECASE)
        if match:
            prompt = match.group(1).strip()
            if len(prompt) >= 2:
                return prompt
    return None


async def check_authorization(update: Update) -> bool:
    """
    Kiểm tra người dùng đã được cấp quyền chat hay chưa.
    Nếu chưa, gửi thông báo kèm User ID để tiện cấp quyền.
    """
    if not update.effective_user:
        return False

    user_id = update.effective_user.id
    if auth_service.is_authorized(user_id):
        return True

    text = (
        "🔒 **Truy cập bị từ chối!**\n\n"
        "Bot Airi Sensei đang hoạt động ở chế độ riêng tư (Private). "
        "Chỉ quản trị viên đã xác thực mới có quyền trò chuyện và sử dụng Agent.\n\n"
        f"🆔 **Telegram ID của bạn:** `{user_id}`\n\n"
        "👉 Nếu bạn có mật mã quản trị, hãy nhập:\n"
        "`/auth <mật_khẩu>`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    return False


async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Xác thực quyền quản trị bằng mật khẩu bí mật
    """
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            f"🔑 **Xác thực quyền sử dụng:**\n\n"
            f"ID của bạn: `{user_id}`\n\n"
            "Vui lòng nhập lệnh kèm mật mã:\n`/auth <mật_khẩu>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    passcode = " ".join(context.args).strip()
    if auth_service.authenticate(user_id, passcode):
        await update.message.reply_text(
            f"✅ **Xác thực thành công!** 🌸\n\n"
            f"Chào mừng anh! Quyền truy cập AI Agent Airi Sensei đã được kích hoạt cho tài khoản `{user_id}`.\n\n"
            "Bây giờ anh có thể tự do trò chuyện, tìm kiếm web, đọc link, làm toán và vẽ tranh rồi nhé! ✨",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text("❌ Mật khẩu xác thực không đúng. Vui lòng kiểm tra lại!")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name if update.effective_user else "bạn"
    user_id = update.effective_user.id

    is_auth = auth_service.is_authorized(user_id)
    status_tag = "🟢 *(Đã xác thực)*" if is_auth else "🔒 *(Chưa xác thực - Dùng /auth <pass>)*"

    text = (
        f"🌸 **Chào {user_name}! Mình là Airi Sensei (@AiriSenseiBot)** 🌸\n"
        f"Trạng thái tài khoản: {status_tag}\n\n"
        "Mình là **AI Agent tự chủ (Autonomous ReAct Agent)** được trang bị đầy đủ công cụ làm việc:\n\n"
        "🔍 **1. Tìm kiếm web thời gian thực (`web_search`):** Cập nhật tin tức, thời tiết, giá cả hôm nay.\n"
        "📖 **2. Đọc & tóm tắt trang web (`read_webpage`):** Gửi link URL để mình đọc và trích xuất nội dung.\n"
        "🎨 **3. Vẽ tranh nghệ thuật (`generate_image`):** Tạo ảnh Flux 1024x1024 theo mọi mô tả.\n"
        "🧮 **4. Tính toán chính xác (`calculate`):** Xử lý các phép tính toán học phức tạp.\n"
        "⏱️ **5. Thời gian thực tế (`get_current_time`):** Kiểm tra ngày giờ hiện tại ở Việt Nam.\n\n"
        "📌 **Các lệnh hữu ích:**\n"
        "• `/auth <mật_khẩu>` - Kích hoạt quyền truy cập bot\n"
        "• `/help` - Xem tài liệu & ví dụ chi tiết\n"
        "• `/image <mô tả>` - Vẽ ảnh trực tiếp bằng Flux\n"
        "• `/models` - Xem danh sách AI Model & Fallback\n"
        "• `/status` - Uptime & trạng thái Agent\n"
        "• `/clear` - Làm mới ngữ cảnh hội thoại\n\n"
        "Bạn hãy thử nhắn một câu hỏi hoặc yêu cầu bất kỳ cho mình nhé! ✨"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📚 **HƯỚNG DẪN SỬ DỤNG AI AGENT AIRI SENSEI**\n\n"
        "🔐 **Xác thực quyền riêng tư:**\n"
        "• Gõ `/auth <mật_khẩu>` để kích hoạt quyền truy cập.\n\n"
        "🤖 **Khả năng tự chủ của Airi Agent:**\n"
        "Bạn chỉ cần nhắn tin tự nhiên, Airi sẽ tự động suy nghĩ và chọn công cụ phù hợp:\n\n"
        "• 🔍 *'Tin tức công nghệ mới nhất hôm nay có gì hot?'* → Airi tìm kiếm trên web.\n"
        "• 📖 *'Đọc giúp mình trang web https://vnexpress.net và tóm tắt.'* → Airi cào và đọc dữ liệu.\n"
        "• 🧮 *'Tính (450 * 12) + (3500 / 7) giúp mình'* → Airi tính toán số học chuẩn xác.\n"
        "• ⏱️ *'Hôm nay là thứ mấy và mấy giờ rồi?'* → Airi kiểm tra giờ Việt Nam.\n"
        "• 🎨 *'Vẽ cho mình một chú mèo phi hành gia trong dải ngân hà'* → Airi tự vẽ và gửi ảnh.\n\n"
        "🔹 **Lệnh tạo ảnh trực tiếp:**\n"
        "• `/image <mô tả>` (Ví dụ: `/image phong cảnh Đà Lạt mộng mơ lúc hoàng hôn anime 4k`)\n\n"
        "🔹 **Quản trị hệ thống:**\n"
        "• `/clear`: Xóa lịch sử nhớ để bắt đầu chủ đề mới\n"
        "• `/models`: Xem các model AI và cơ chế dự phòng\n"
        "• `/status`: Kiểm tra độ trễ mạng và Uptime server 24/7"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_authorization(update):
        return

    fallback_list = ", ".join(settings.fallback_models_list)
    or_free_list = ", ".join(settings.openrouter_free_models_list)
    text = (
        "🤖 **CẤU HÌNH AI AGENT MODELS & CASCADING FALLBACK**\n\n"
        f"🥇 **OpenRouter Free Tier:** `{or_free_list}`\n"
        f"🥈 **B.AI Models:** `{settings.AI_PRIMARY_MODEL}`, `{fallback_list}`\n"
        f"🌸 **Zero-Failure Fallback:** `openai-fast` (Pollinations GPT-OSS 20B)\n"
        f"🎨 **Image Engine:** `{settings.IMAGE_MODEL}` (Flux 1024x1024)\n\n"
        "💡 *Cơ chế:* Tự động luân chuyển model thông minh khi gặp lỗi quota hoặc nghẽn mạng!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uptime_sec = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    user_id = update.effective_user.id if update.effective_user else 0
    is_auth = auth_service.is_authorized(user_id)

    text = (
        "⚡ **TRẠNG THÁI HỆ THỐNG AIRI SENSEI**\n\n"
        f"🟢 **Trạng thái:** Online 24/7 (Render Web Service)\n"
        f"🤖 **Chế độ hoạt động:** Autonomous AI Agent (ReAct Loop + Tools)\n"
        f"⏱️ **Thời gian hoạt động (Uptime):** {uptime_str}\n"
        f"🔐 **Chế độ bảo vệ:** {'Bật (Private Whitelist)' if settings.AUTH_ENABLED else 'Mở (Public)'}\n"
        f"👤 **Tài khoản của bạn:** {'Đã cấp quyền ✅' if is_auth else 'Chưa cấp quyền ❌'}\n"
        f"🛠️ **Công cụ tích hợp:** Web Search, Read Webpage, Calculator, VN Time, Image Gen\n"
        f"🎨 **Image Engine:** `{settings.IMAGE_MODEL}` (Flux)\n"
        f"🌐 **HTTP Health Server:** Port `{settings.PORT}` OK"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_authorization(update):
        return

    user_id = update.effective_user.id
    chat_service.clear_history(user_id)
    airi_agent.clear_history(user_id)
    await update.message.reply_text(
        "🧹 Mình đã làm mới bộ nhớ trò chuyện và ngữ cảnh Agent rồi! Chúng ta bắt đầu nhiệm vụ mới nhé! ✨"
    )


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_authorization(update):
        return

    if not context.args:
        await update.message.reply_text(
            "🎨 Bạn hãy nhập mô tả tranh muốn vẽ nhé!\n\n"
            "👉 *Ví dụ:* `/image một chú mèo phi hành gia bay ngoài vũ trụ phong cách anime 4k`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    prompt = " ".join(context.args).strip()
    await _execute_image_generation(update, prompt)


async def _execute_image_generation(update: Update, prompt: str) -> None:
    cleaned = clean_prompt(prompt)
    status_msg = await update.message.reply_text(
        "🎨 *Airi đang vẽ tranh cho bạn, đợi xíu nhé...*",
        parse_mode=ParseMode.MARKDOWN,
    )
    await update.message.reply_chat_action(ChatAction.UPLOAD_PHOTO)

    try:
        image_bytes, model_used = await image_service.generate_image(cleaned)
        await status_msg.delete()
        caption = f"🎨 **Tranh của bạn:**\n_{cleaned}_\n\n*(Model: {model_used})*"
        await update.message.reply_photo(
            photo=io.BytesIO(image_bytes),
            caption=caption[:1024],
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("Error generating image: %s", e)
        await status_msg.edit_text(f"❌ Ôi, không vẽ được ảnh rồi: {e}\nBạn hãy thử lại với mô tả khác nhé!")


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    if not user_message:
        return

    # Kiểm tra phân quyền xác thực trước khi xử lý
    if not await check_authorization(update):
        return

    user_id = update.effective_user.id
    await update.message.reply_chat_action(ChatAction.TYPING)

    status_msg = None

    async def on_agent_status(status_text: str):
        nonlocal status_msg
        try:
            if status_msg is None:
                status_msg = await update.message.reply_text(status_text)
            else:
                await status_msg.edit_text(status_text)
        except Exception as err:
            logger.debug("Could not update status message: %s", err)

    try:
        result = await airi_agent.run(
            user_id=user_id,
            user_input=user_message,
            on_status_update=on_agent_status,
        )

        # Xóa tin nhắn trạng thái trung gian nếu có
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass

        # 1. Gửi ảnh nếu agent đã sinh ảnh trong quá trình thực thi
        for img_bytes, prompt_desc in result.images:
            cleaned = clean_prompt(prompt_desc)
            caption = f"🎨 **Tranh tạo bởi Airi:**\n_{cleaned}_\n\n*(Engine: {settings.IMAGE_MODEL})*"
            await update.message.reply_photo(
                photo=io.BytesIO(img_bytes),
                caption=caption[:1024],
                parse_mode=ParseMode.MARKDOWN,
            )

        # 2. Gửi câu trả lời bằng văn bản
        text_reply = result.text.strip()
        if not text_reply and result.images:
            text_reply = "Airi đã vẽ xong tranh cho bạn rồi đây! ✨"

        # Hiển thị các tool đã sử dụng nếu có
        if result.tools_used:
            unique_tools = list(dict.fromkeys(result.tools_used))
            tools_str = ", ".join(unique_tools)
            footer = f"\n\n_— Airi Agent ⚡ [{tools_str}]_"
        else:
            footer = "\n\n_— Airi Sensei 🌸_"

        full_reply = text_reply + footer
        try:
            await update.message.reply_text(full_reply, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(full_reply)

    except Exception as e:
        logger.error("Error in text handler: %s", e)
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass
        await update.message.reply_text(
            f"Dạ có lỗi nhỏ xảy ra khi Airi xử lý: {e}. Bạn thử lại nhé!"
        )
