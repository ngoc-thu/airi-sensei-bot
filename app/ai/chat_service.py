import logging
from typing import Dict, List, Tuple
from openai import AsyncOpenAI
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

AIRI_SYSTEM_PROMPT = (
    "Bạn là Airi Sensei (Cô giáo Airi) - một trợ lý AI thông minh, nhiệt tình, tinh tế và vui vẻ. "
    "Bạn luôn trả lời người dùng bằng tiếng Việt tự nhiên, chuẩn xác, giải thích dễ hiểu từ lập trình, "
    "công nghệ, toán học cho đến học tập và đời sống. Bạn xưng hô là 'Airi' hoặc 'mình' và gọi người dùng "
    "là 'bạn' hoặc 'anh/chị'. Khi giải thích code hoặc hướng dẫn kỹ thuật, bạn trình bày rõ ràng với ví dụ trực quan."
)


class ChatService:
    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.history: Dict[int, List[Dict[str, str]]] = {}
        self._client: AsyncOpenAI = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.settings.AI_BASE_URL,
                api_key=self.settings.AI_API_KEY or "none",
                timeout=30.0,
            )
        return self._client

    def clear_history(self, user_id: int) -> None:
        if user_id in self.history:
            del self.history[user_id]
            logger.info("Cleared conversation history for user %s", user_id)

    def _get_user_history(self, user_id: int) -> List[Dict[str, str]]:
        if user_id not in self.history:
            self.history[user_id] = []
        return self.history[user_id]

    async def ask(self, user_id: int, message: str) -> Tuple[str, str]:
        """
        Gửi prompt qua danh sách model với cơ chế Cascading Fallback.
        Trả về (câu_trả_lời, model_được_dùng).
        """
        user_history = self._get_user_history(user_id)
        user_history.append({"role": "user", "content": message})

        # Giữ tối đa 10 tin nhắn gần nhất
        if len(user_history) > 10:
            user_history = user_history[-10:]
            self.history[user_id] = user_history

        messages = [{"role": "system", "content": AIRI_SYSTEM_PROMPT}] + user_history

        # Dàn model cascading fallback
        candidate_models = [self.settings.AI_PRIMARY_MODEL] + self.settings.fallback_models_list

        client = self._get_client()

        for model in candidate_models:
            try:
                logger.info("Trying model: %s for user %s", model, user_id)
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1500,
                    temperature=0.7,
                )
                if response.choices and response.choices[0].message.content:
                    reply = response.choices[0].message.content.strip()
                    user_history.append({"role": "assistant", "content": reply})
                    logger.info("Successfully got response from model: %s", model)
                    return reply, model
            except Exception as e:
                logger.warning(
                    "Model %s failed with error: %s. Switching to next fallback...",
                    model,
                    e
                )

        # Fallback an toàn nếu tất cả các model đều gặp sự cố (ví dụ tài khoản hết quota)
        logger.error("All AI models in cascade failed. Returning graceful fallback.")
        fallback_reply = (
            f"Chào bạn, mình là **Airi Sensei**! 🌸\n\n"
            f"Mình đã nhận được câu hỏi của bạn: *\"{message}\"*\n\n"
            f"Hiện tại kết nối AI đang bận hoặc đang được nâng cấp hạn ngạch (quota). "
            f"Bạn hãy thử lại sau giây lát nhé! Trong lúc đó bạn có thể dùng lệnh `/image <mô tả>` "
            f"để vẽ tranh nhé!"
        )
        return fallback_reply, "fallback-persona"
