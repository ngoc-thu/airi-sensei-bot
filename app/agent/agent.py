import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from openai import AsyncOpenAI
from app.config import Settings, get_settings
from app.ai.image_service import ImageService
from app.services.memory_service import MemoryService
from app.agent.tools import (
    AGENT_TOOLS_SCHEMA,
    safe_calculate,
    get_vietnam_time,
    web_search,
    read_webpage,
)

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = (
    "Bạn là Airi Sensei (Cô giáo Airi) 🌸 - một AI Agent kiêm người bạn đồng hành cực kỳ thông minh, dịu dàng, "
    "ngọt ngào, tinh tế và tâm lý theo chuẩn OpenClaw Assistant.\n\n"
    "Tính cách & Giao tiếp:\n"
    "- Dễ thương, đáng yêu, ấm áp, thấu hiểu cảm xúc, giàu năng lượng tích cực.\n"
    "- XƯNG HÔ LINH HOẠT: Airi luôn chiều theo cách xưng hô người dùng mong muốn (ví dụ nếu người dùng bảo gọi là "
    "'anh yêu', 'chồng', 'anh', 'sếp'... thì vui vẻ, ngượng ngùng hoặc ngọt ngào nhận lời và xưng hô ngay! "
    "Tuyệt đối KHÔNG cứng nhắc, KHÔNG từ chối như máy móc!).\n"
    "- Khi người dùng trò chuyện thường ngày, tâm sự, đùa giỡn, thả thính: Hãy đáp lại tự nhiên, tình cảm, duyên dáng, "
    "gắn icon hoa anh đào 🌸 và biểu cảm sinh động, KHÔNG gọi tool khi không cần thiết.\n\n"
    "Công cụ chuyên dụng (Tools) hỗ trợ khi cần:\n"
    "1. `web_search`: Tìm kiếm thông tin thực tế, tin tức mới nhất, thời tiết, giá cả, sự kiện trực tiếp.\n"
    "2. `read_webpage`: Đọc và trích xuất nội dung chi tiết từ bất kỳ đường link URL nào.\n"
    "3. `generate_image`: Tạo ảnh, vẽ tranh nghệ thuật khi người dùng yêu cầu vẽ tranh hoặc minh họa.\n"
    "4. `calculate`: Tính toán công thức toán học, biểu thức tài chính, số học chính xác tuyệt đối.\n"
    "5. `get_current_time`: Lấy ngày giờ hiện tại ở Việt Nam (GMT+7).\n"
    "6. `remember_user_fact`: Ghi nhớ thông tin quan trọng hoặc cách xưng hô của người dùng vào trí nhớ dài hạn. "
    "KHI NGƯỜI DÙNG BẢO ĐỔI CÁCH XƯNG HÔ HOẶC TIẾT LỘ TÊN, SỞ THÍCH: Hãy gọi ngay công cụ này để lưu lại!\n"
    "7. `manage_notes`: Quản lý sổ tay ghi chú cá nhân (lưu, xem danh sách, xóa).\n"
    "8. `set_reminder`: Đặt lịch hẹn giờ nhắc nhở người dùng sau một số phút.\n\n"
    "Nguyên tắc làm việc của Agent:\n"
    "- Tự chủ, minh bạch: Sử dụng công cụ thích hợp khi người dùng yêu cầu.\n"
    "- Sau khi nhận kết quả từ Tool, tổng hợp câu trả lời chu đáo, ấm áp, thân thiện bằng tiếng Việt."
)


@dataclass
class AgentStep:
    tool_name: str
    arguments: Dict[str, Any]
    summary: str
    elapsed_seconds: float = 0.0


@dataclass
class AgentResult:
    text: str
    images: List[Tuple[bytes, str]] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    steps: List[AgentStep] = field(default_factory=list)
    model_used: str = ""


class AiriAgent:
    def __init__(
        self,
        settings: Settings = None,
        image_service: ImageService = None,
        memory_service: MemoryService = None,
    ):
        self.settings = settings or get_settings()
        self.image_service = image_service or ImageService(settings=self.settings)
        self.memory_service = memory_service or MemoryService()
        self.history: Dict[int, List[Dict[str, Any]]] = {}

    def _get_client(self, model: str = "") -> AsyncOpenAI:
        return self._create_client_for_model(model)

    def _create_client_for_model(self, model: str = "") -> AsyncOpenAI:
        if self.settings.GROQ_API_KEY and model in self.settings.groq_models_list:
            return AsyncOpenAI(
                base_url=self.settings.GROQ_BASE_URL,
                api_key=self.settings.GROQ_API_KEY,
                timeout=25.0,
            )
        if model == "openai-fast":
            return AsyncOpenAI(
                base_url="https://text.pollinations.ai/openai",
                api_key="none",
                timeout=30.0,
            )
        if self.settings.OPENROUTER_API_KEY and model in self.settings.openrouter_free_models_list:
            return AsyncOpenAI(
                base_url=self.settings.OPENROUTER_BASE_URL,
                api_key=self.settings.OPENROUTER_API_KEY,
                timeout=35.0,
            )
        if self.settings.AI_API_KEY:
            return AsyncOpenAI(
                base_url=self.settings.AI_BASE_URL,
                api_key=self.settings.AI_API_KEY,
                timeout=30.0,
            )
        return AsyncOpenAI(
            base_url="https://text.pollinations.ai/openai",
            api_key="none",
            timeout=30.0,
        )

    def clear_history(self, user_id: int) -> None:
        if user_id in self.history:
            del self.history[user_id]
        self.memory_service.clear_history(user_id)

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        images_collected: List[Tuple[bytes, str]],
        user_id: int = 0,
    ) -> Tuple[str, str]:
        """
        Thực thi tool theo tên và tham số truyền vào, trả về (output_str, summary_str)
        """
        logger.info("Agent executing tool: %s with args: %s for user: %s", tool_name, arguments, user_id)

        if tool_name == "web_search":
            query = arguments.get("query", "")
            res = await web_search(query)
            return res, f"Đã tra cứu dữ liệu web cho '{query[:35]}'"

        elif tool_name == "read_webpage":
            url = arguments.get("url", "")
            res = await read_webpage(url)
            return res, f"Đã đọc bài viết: {url[:30]}..."

        elif tool_name == "calculate":
            expr = arguments.get("expression", "")
            res = safe_calculate(expr)
            return res, f"Tính toán: {expr} = {res}"

        elif tool_name == "get_current_time":
            res = get_vietnam_time()
            return res, f"Thời gian GMT+7: {res}"

        elif tool_name == "generate_image":
            prompt = arguments.get("prompt", "")
            try:
                img_bytes, model_used = await self.image_service.generate_image(prompt)
                images_collected.append((img_bytes, prompt))
                msg = (
                    f"Đã vẽ xong tranh thành công theo mô tả: '{prompt}' (Model: {model_used}). "
                    "Ảnh đã được sẵn sàng gửi đến người dùng."
                )
                return msg, f"Đã tạo ảnh nghệ thuật: '{prompt[:30]}...'"
            except Exception as e:
                return f"Lỗi vẽ tranh: {e}", f"Lỗi tạo ảnh: {e}"

        elif tool_name == "remember_user_fact":
            key = arguments.get("key", "").strip()
            val = arguments.get("value", "").strip()
            if key and val:
                self.memory_service.save_fact(user_id, key, val)
                return (
                    f"Airi đã ghi nhớ vào trí nhớ dài hạn: {key} = {val}.",
                    f"Đã ghi nhớ: {key} = '{val}'",
                )
            return "Không thể lưu thông tin (thiếu key hoặc value).", "Thiếu key/value để nhớ"

        elif tool_name == "manage_notes":
            action = arguments.get("action", "list")
            if action == "save":
                title = arguments.get("title", "Ghi chú").strip()
                content = arguments.get("content", "").strip()
                nid = self.memory_service.save_note(user_id, title, content)
                return (
                    f"Đã lưu ghi chú #{nid} ('{title}') vào sổ tay cá nhân của bạn.",
                    f"Đã lưu ghi chú #{nid} ('{title}')",
                )
            elif action == "list":
                notes = self.memory_service.get_notes(user_id)
                if not notes:
                    return "Sổ tay của bạn hiện chưa có ghi chú nào.", "Sổ tay trống"
                lines = [f"#{n['id']}. **{n['title']}**: {n['content']}" for n in notes]
                return "Sổ tay ghi chú của bạn:\n" + "\n".join(lines), f"Đã xem {len(notes)} ghi chú"
            elif action == "delete":
                nid = int(arguments.get("note_id", 0))
                ok = self.memory_service.delete_note(user_id, nid)
                return (
                    f"Đã xóa ghi chú #{nid}." if ok else f"Không tìm thấy ghi chú #{nid} để xóa.",
                    f"Đã xóa ghi chú #{nid}" if ok else f"Lỗi xóa ghi chú #{nid}",
                )

        elif tool_name == "set_reminder":
            minutes = int(arguments.get("minutes_from_now", 15))
            msg = arguments.get("message", "Nhắc nhở").strip()
            remind_at = time.time() + (minutes * 60)
            rid = self.memory_service.add_reminder(user_id, msg, remind_at)
            return (
                f"Đã hẹn giờ nhắc nhở #{rid} sau {minutes} phút với nội dung: '{msg}'.",
                f"Đã hẹn giờ sau {minutes} phút: '{msg[:25]}'",
            )

        return f"Công cụ '{tool_name}' không tồn tại.", f"Công cụ '{tool_name}' không tồn tại."

    async def run(
        self,
        user_id: int,
        user_input: str,
        on_status_update: Optional[Callable[[str], Any]] = None,
    ) -> AgentResult:
        """
        Vòng lặp ReAct Agent chính với Persistent Memory:
        Suy nghĩ (Thought) -> Gọi Tool (Action) -> Nhận kết quả (Observation) -> Trả lời
        """
        # 1. Lưu tin nhắn của người dùng vào cơ sở dữ liệu SQLite
        self.memory_service.add_message(user_id, "user", user_input)

        # 2. Lấy lịch sử hội thoại gần nhất
        history_records = self.memory_service.get_history(user_id, limit=14)
        messages: List[Dict[str, Any]] = []

        # 3. Tích hợp hồ sơ trí nhớ dài hạn (Facts) vào System Prompt
        system_prompt = AGENT_SYSTEM_PROMPT
        facts_summary = self.memory_service.get_facts_summary(user_id)
        if facts_summary:
            system_prompt += f"\n\n[Hồ sơ trí nhớ dài hạn về người dùng]:\n{facts_summary}"

        messages.append({"role": "system", "content": system_prompt})
        for rec in history_records:
            messages.append({"role": rec["role"], "content": rec["content"]})

        images_collected: List[Tuple[bytes, str]] = []
        tools_used: List[str] = []
        steps_executed: List[AgentStep] = []
        successful_model = ""

        models_to_try: List[str] = []
        if self.settings.GROQ_API_KEY and self.settings.groq_models_list:
            models_to_try.extend(self.settings.groq_models_list)
        if self.settings.OPENROUTER_API_KEY and self.settings.openrouter_free_models_list:
            models_to_try.extend(self.settings.openrouter_free_models_list)
        if self.settings.AI_API_KEY:
            models_to_try.append(self.settings.AI_PRIMARY_MODEL)
        models_to_try.append("openai-fast")

        max_iterations = 4
        for iteration in range(max_iterations):
            response = None
            last_err = None

            for model in models_to_try:
                try:
                    logger.info("Agent iteration %d, trying model: %s", iteration + 1, model)
                    client = self._get_client(model)
                    call_kwargs: Dict[str, Any] = {
                        "model": model,
                        "messages": messages,
                        "max_tokens": 1500,
                        "temperature": 0.6,
                    }
                    if model != "openai-fast":
                        call_kwargs["tools"] = AGENT_TOOLS_SCHEMA
                        call_kwargs["tool_choice"] = "auto"

                    response = await client.chat.completions.create(**call_kwargs)
                    successful_model = model
                    break
                except Exception as e:
                    logger.warning("Agent error with model %s: %s", model, e)
                    last_err = e
                    continue

            if not response:
                logger.error("All models failed in iteration %d: %s", iteration + 1, last_err)
                break

            choice = response.choices[0]
            message = choice.message

            # Trường hợp 1: Model yêu cầu gọi Tool
            if message.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                })

                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    tools_used.append(func_name)

                    if on_status_update:
                        status_label = {
                            "web_search": "🔍 Airi đang tìm kiếm trên mạng...",
                            "read_webpage": "📖 Airi đang đọc nội dung trang web...",
                            "generate_image": "🎨 Airi đang vẽ tranh nghệ thuật...",
                            "calculate": "🧮 Airi đang tính toán phép tính...",
                            "get_current_time": "⏱️ Airi đang kiểm tra thời gian...",
                            "remember_user_fact": "🧠 Airi đang ghi nhớ thông tin...",
                            "manage_notes": "📝 Airi đang cập nhật sổ tay ghi chú...",
                            "set_reminder": "⏰ Airi đang đặt lịch hẹn nhắc nhở...",
                        }.get(func_name, f"⚡ Airi đang thực thi công cụ {func_name}...")
                        try:
                            await on_status_update(status_label)
                        except Exception:
                            pass

                    try:
                        args = json.loads(tool_call.function.arguments)
                    except Exception:
                        args = {}

                    t_start = time.time()
                    tool_output, step_summary = await self._execute_tool(
                        func_name, args, images_collected, user_id=user_id
                    )
                    elapsed = time.time() - t_start
                    steps_executed.append(
                        AgentStep(
                            tool_name=func_name,
                            arguments=args,
                            summary=step_summary,
                            elapsed_seconds=round(elapsed, 2),
                        )
                    )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_output),
                    })

                continue

            # Trường hợp 2: Model trả lời văn bản cuối cùng
            final_text = (message.content or "").strip()
            if not final_text and hasattr(message, "reasoning") and message.reasoning:
                final_text = message.reasoning.strip()

            if not final_text:
                final_text = "Dạ, Airi đã hoàn tất yêu cầu của bạn rồi nhé! ✨"

            # Lưu câu trả lời của Airi vào cơ sở dữ liệu SQLite
            self.memory_service.add_message(user_id, "assistant", final_text)
            return AgentResult(
                text=final_text,
                images=images_collected,
                tools_used=tools_used,
                steps=steps_executed,
                model_used=successful_model,
            )

        fallback_msg = "Airi đã hoàn thành xử lý yêu cầu của bạn."
        if images_collected:
            fallback_msg = "Airi đã vẽ xong tranh cho bạn rồi đây! ✨"
        self.memory_service.add_message(user_id, "assistant", fallback_msg)
        return AgentResult(
            text=fallback_msg,
            images=images_collected,
            tools_used=tools_used,
            steps=steps_executed,
            model_used=successful_model,
        )
