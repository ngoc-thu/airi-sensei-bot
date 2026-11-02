import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from openai import AsyncOpenAI
from app.config import Settings, get_settings
from app.ai.image_service import ImageService
from app.agent.tools import (
    AGENT_TOOLS_SCHEMA,
    safe_calculate,
    get_vietnam_time,
    web_search,
    read_webpage,
)

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = (
    "Bạn là Airi Sensei (Cô giáo Airi) - một AI Agent thông minh, nhiệt tình, có khả năng hành động tự chủ. "
    "Bạn được trang bị các công cụ chuyên dụng (Tools) để giải quyết nhiệm vụ:\n"
    "1. `web_search`: Tìm kiếm thông tin thực tế, tin tức mới nhất hôm nay, thời tiết, giá cả, sự kiện trực tiếp.\n"
    "2. `read_webpage`: Đọc và phân tích nội dung chi tiết từ bất kỳ đường link URL nào.\n"
    "3. `generate_image`: Tạo ảnh, vẽ tranh nghệ thuật khi người dùng yêu cầu vẽ hoặc minh họa.\n"
    "4. `calculate`: Tính toán công thức toán học, biểu thức tài chính, số học chính xác tuyệt đối.\n"
    "5. `get_current_time`: Lấy ngày giờ hiện tại ở Việt Nam (GMT+7).\n\n"
    "Nguyên tắc làm việc của Agent:\n"
    "- Khi người dùng hỏi thông tin cần cập nhật thời gian thực, thời tiết, giá cả: HÃY GỌI `web_search`.\n"
    "- Khi người dùng gửi một đường link: HÃY GỌI `read_webpage`.\n"
    "- Khi người dùng yêu cầu vẽ tranh, tạo ảnh: HÃY GỌI `generate_image`.\n"
    "- Khi cần làm toán: HÃY GỌI `calculate`.\n"
    "- Sau khi nhận kết quả từ Tool, hãy tổng hợp câu trả lời một cách tự nhiên, chu đáo, thân thiện bằng tiếng Việt. "
    "Xưng hô là 'Airi' hoặc 'mình' và gọi người dùng là 'bạn' hoặc 'anh/chị'."
)


@dataclass
class AgentResult:
    text: str
    images: List[Tuple[bytes, str]] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)


class AiriAgent:
    def __init__(self, settings: Settings = None, image_service: ImageService = None):
        self.settings = settings or get_settings()
        self.image_service = image_service or ImageService(settings=self.settings)
        self.history: Dict[int, List[Dict[str, Any]]] = {}

    def _get_client(self, model: str = "") -> AsyncOpenAI:
        return self._create_client_for_model(model)

    def _create_client_for_model(self, model: str = "") -> AsyncOpenAI:
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

    def _get_user_history(self, user_id: int) -> List[Dict[str, Any]]:
        if user_id not in self.history:
            self.history[user_id] = []
        return self.history[user_id]

    def clear_history(self, user_id: int) -> None:
        if user_id in self.history:
            del self.history[user_id]

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        images_collected: List[Tuple[bytes, str]],
    ) -> str:
        """
        Thực thi tool theo tên và tham số truyền vào
        """
        logger.info("Agent executing tool: %s with args: %s", tool_name, arguments)

        if tool_name == "web_search":
            query = arguments.get("query", "")
            return await web_search(query)

        elif tool_name == "read_webpage":
            url = arguments.get("url", "")
            return await read_webpage(url)

        elif tool_name == "calculate":
            expr = arguments.get("expression", "")
            return safe_calculate(expr)

        elif tool_name == "get_current_time":
            return get_vietnam_time()

        elif tool_name == "generate_image":
            prompt = arguments.get("prompt", "")
            try:
                img_bytes, model_used = await self.image_service.generate_image(prompt)
                images_collected.append((img_bytes, prompt))
                return (
                    f"Đã vẽ xong tranh thành công theo mô tả: '{prompt}' (Model: {model_used}). "
                    "Ảnh đã được sẵn sàng gửi đến người dùng."
                )
            except Exception as e:
                return f"Lỗi vẽ tranh: {e}"

        return f"Công cụ '{tool_name}' không tồn tại."

    async def run(
        self,
        user_id: int,
        user_input: str,
        on_status_update: Optional[Callable[[str], Any]] = None,
    ) -> AgentResult:
        """
        Vòng lặp ReAct Agent chính:
        Suy nghĩ (Thought) -> Gọi Tool (Action) -> Nhận kết quả (Observation) -> Trả lời
        """
        user_history = self._get_user_history(user_id)
        user_history.append({"role": "user", "content": user_input})

        if len(user_history) > 12:
            user_history = user_history[-12:]
            self.history[user_id] = user_history

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT}
        ] + list(user_history)

        images_collected: List[Tuple[bytes, str]] = []
        tools_used: List[str] = []

        models_to_try: List[str] = []
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
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=AGENT_TOOLS_SCHEMA,
                        tool_choice="auto",
                        max_tokens=1500,
                        temperature=0.6,
                    )
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
                        }.get(func_name, f"⚡ Airi đang thực thi công cụ {func_name}...")
                        try:
                            await on_status_update(status_label)
                        except Exception:
                            pass

                    try:
                        args = json.loads(tool_call.function.arguments)
                    except Exception:
                        args = {}

                    tool_output = await self._execute_tool(func_name, args, images_collected)

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

            user_history.append({"role": "assistant", "content": final_text})
            return AgentResult(text=final_text, images=images_collected, tools_used=tools_used)

        # Nếu vòng lặp kết thúc mà chưa có câu trả lời hoàn chỉnh
        fallback_msg = "Airi đã hoàn thành xử lý yêu cầu của bạn."
        if images_collected:
            fallback_msg = "Airi đã vẽ xong tranh cho bạn rồi đây! ✨"
        return AgentResult(text=fallback_msg, images=images_collected, tools_used=tools_used)
