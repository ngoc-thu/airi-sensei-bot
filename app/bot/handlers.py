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

    is_owner = (user_id == 5556841083) or (user_id in settings.allowed_user_ids_list)
    is_auth = auth_service.is_authorized(user_id)
    status_tag = "👑 *(Chủ nhân / Quản trị viên)*" if is_owner else (
        "🟢 *(Đã xác thực)*" if is_auth else "🔒 *(Chưa xác thực - Dùng /auth <pass>)*"
    )

    text = (
        f"🌸 **Chào {user_name}! Mình là Airi Sensei (@AiriSenseiBot)** 🌸\n"
        f"Trạng thái tài khoản: {status_tag}\n\n"
        "Mình là **AI Agent tự chủ (OpenClaw Architecture)** được trang bị đầy đủ công cụ & trí nhớ dài hạn:\n\n"
        "🧠 **1. Trí nhớ vĩnh viễn (Long-Term Memory):** Ghi nhớ sở thích, tên gọi và ngữ cảnh không bao giờ quên.\n"
        "📝 **2. Sổ tay ghi chú (`manage_notes`):** Lưu trữ, quản lý các ghi chú cá nhân của bạn.\n"
        "⏰ **3. Đặt lịch nhắc nhở (`set_reminder`):** Hẹn giờ và tự động gửi tin nhắn Telegram nhắc việc đúng giờ.\n"
        "🔍 **4. Tìm kiếm web thời gian thực (`web_search`):** Tra cứu tỷ giá, giá vàng, thời tiết, tin tức mới nhất.\n"
        "📖 **5. Đọc & tóm tắt link (`read_webpage`):** Cào và phân tích nội dung chi tiết từ bất kỳ URL nào.\n"
        "🎨 **6. Vẽ tranh nghệ thuật (`generate_image`):** Tạo ảnh nghệ thuật bằng engine Flux 1024x1024.\n"
        "🧮 **7. Tính toán chính xác (`calculate`):** Giải toán học, tài chính chính xác tuyệt đối.\n\n"
        "📌 **Các lệnh hữu ích:**\n"
        "• `/help` - Xem hướng dẫn & kịch bản chi tiết\n"
        "• `/status` - Xem trạng thái hệ thống & trí nhớ\n"
        "• `/clear` - Làm mới ngữ cảnh hội thoại\n"
        "• `/image <mô tả>` - Vẽ ảnh trực tiếp\n\n"
        "Bạn hãy trò chuyện hoặc giao nhiệm vụ bất kỳ cho mình nhé! ✨"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📚 **HƯỚNG DẪN SỬ DỤNG AIRI SENSEI (OPENCLAW AGENT)**\n\n"
        "🤖 **Khả năng tự chủ & các câu lệnh mẫu:**\n\n"
        "• 🧠 **Ghi nhớ cá nhân:** *'Anh tên là Tiến, nhớ nha em'*, *'Từ giờ gọi anh là anh yêu nha'*\n"
        "• 📝 **Sổ tay ghi chú:** *'Lưu ghi chú: Mua tài liệu AI'*, *'Xem danh sách ghi chú của anh'*\n"
        "• ⏰ **Hẹn giờ nhắc nhở:** *'Nhắc anh sau 30 phút đi uống nước'*, *'Sau 60 phút nhắc anh họp nhóm'*\n"
        "• 🔍 **Tra cứu thời gian thực:** *'Giá vàng hôm nay bao nhiêu?'*, *'Thời tiết Hà Nội hôm nay'*\n"
        "• 📖 **Đọc link bài viết:** *'Đọc trang https://vnexpress.net và tóm tắt 3 ý chính'*\n"
        "• 🎨 **Vẽ tranh nghệ thuật:** *'Vẽ cho mình chú mèo phi hành gia ngoài vũ trụ'* hoặc `/image ...`\n"
        "• 🧮 **Tính toán số học:** *'Tính giúp mình: (1250 * 45) / 1.1 + sqrt(144)'*\n\n"
        "🔹 **Các lệnh quản trị:**\n"
        "• `/clear`: Xóa lịch sử nhớ để bắt đầu cuộc trò chuyện mới\n"
        "• `/models`: Xem danh sách AI Model & Cascading Fallback\n"
        "• `/status`: Xem trạng thái Uptime 24/7 và hệ thống"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_authorization(update):
        return

    groq_list = ", ".join(settings.groq_models_list) if settings.GROQ_API_KEY else "Chưa kích hoạt"
    gemini_list = ", ".join(settings.gemini_models_list) if settings.GEMINI_API_KEY else "Chưa kích hoạt"
    fallback_list = ", ".join(settings.fallback_models_list)
    or_free_list = ", ".join(settings.openrouter_free_models_list)
    text = (
        "🤖 **CẤU HÌNH AI AGENT MODELS & CASCADING FALLBACK**\n\n"
        f"⚡ **Tier 1 - Groq Cloud (14.4k RPD / Siêu tốc):** `{groq_list}`\n"
        f"🌟 **Tier 2 - Google Gemini (1.5k RPD / 1M Context):** `{gemini_list}`\n"
        f"🥉 **Tier 3 - OpenRouter Free Tier:** `{or_free_list}`\n"
        f"🔹 **Tier 4 - B.AI Models:** `{settings.AI_PRIMARY_MODEL}`, `{fallback_list}`\n"
        f"🌸 **Tier 5 - Zero-Failure Fallback:** `openai-fast` (Pollinations GPT-OSS 20B)\n"
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
        "⚡ **TRẠNG THÁI HỆ THỐNG AIRI SENSEI (OPENCLAW AGENT)**\n\n"
        f"🟢 **Trạng thái:** Online 24/7 (Render Web Service)\n"
        f"🤖 **Kiến trúc:** OpenClaw Autonomous ReAct Agent\n"
        f"🧠 **Trí nhớ dài hạn:** SQLite Persistent Memory (Vĩnh viễn) ✅\n"
        f"⏱️ **Thời gian hoạt động (Uptime):** {uptime_str}\n"
        f"🔐 **Chế độ bảo vệ:** {'Bật (Private Whitelist)' if settings.AUTH_ENABLED else 'Mở (Public)'}\n"
        f"👤 **Tài khoản của bạn:** {'Đã cấp quyền ✅' if is_auth else 'Chưa cấp quyền ❌'}\n"
        f"🛠️ **Kỹ năng:** Web Search, Read Webpage, Memory Facts, Notes, Reminders, Calculator, Flux Gen\n"
        f"🎨 **Image Engine:** `{settings.IMAGE_MODEL}` (Flux 1024x1024)\n"
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

        # Hiển thị nhật ký hành động (Agent Action Trace) nếu có công cụ được gọi
        if getattr(result, "steps", None):
            trace_lines = []
            tool_icons = {
                "web_search": "🔍",
                "read_webpage": "📖",
                "generate_image": "🎨",
                "calculate": "🧮",
                "get_current_time": "⏱️",
                "remember_user_fact": "🧠",
                "manage_notes": "📝",
                "set_reminder": "⏰",
            }
            for st in result.steps:
                icon = tool_icons.get(st.tool_name, "⚙️")
                trace_lines.append(f"• {icon} *{st.tool_name}*: {st.summary} `({st.elapsed_seconds}s)`")
            trace_block = "\n".join(trace_lines)
            model_info = f" ({result.model_used})" if result.model_used else ""
            footer = (
                f"\n\n────────────────────\n"
                f"🤖 **Nhật ký hành động (Agent Trace):**\n{trace_block}\n"
                f"⚡ _Airi Agent{model_info}_"
            )
        elif result.tools_used:
            unique_tools = list(dict.fromkeys(result.tools_used))
            tools_str = ", ".join(unique_tools)
            model_info = f" ({result.model_used})" if result.model_used else ""
            footer = f"\n\n_— Airi Agent ⚡ [{tools_str}]{model_info}_"
        else:
            model_info = f" ({result.model_used})" if result.model_used else ""
            footer = f"\n\n_— Airi Sensei ✨{model_info}_"

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
