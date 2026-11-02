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
        self._bai_client: AsyncOpenAI = None
        self._openrouter_client: AsyncOpenAI = None

    def _get_bai_client(self) -> AsyncOpenAI:
        if self._bai_client is None:
            self._bai_client = AsyncOpenAI(
                base_url=self.settings.AI_BASE_URL,
                api_key=self.settings.AI_API_KEY or "none",
                timeout=25.0,
            )
        return self._bai_client

    def _get_openrouter_client(self) -> AsyncOpenAI:
        if self._openrouter_client is None and self.settings.OPENROUTER_API_KEY:
            self._openrouter_client = AsyncOpenAI(
                base_url=self.settings.OPENROUTER_BASE_URL,
                api_key=self.settings.OPENROUTER_API_KEY,
                timeout=25.0,
            )
        return self._openrouter_client

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
        Gửi prompt qua chuỗi model phân tầng:
        1. OpenRouter (các model hoàn toàn miễn phí ':free') nếu có key.
        2. B.AI (nếu có key & còn quota).
        3. Pollinations Free AI Engine ('openai-fast' - 100% free, 0 key).
        4. Safe Persona Fallback.
        """
        user_history = self._get_user_history(user_id)
        user_history.append({"role": "user", "content": message})

        # Giữ tối đa 10 tin nhắn gần nhất
        if len(user_history) > 10:
            user_history = user_history[-10:]
            self.history[user_id] = user_history

        messages = [{"role": "system", "content": AIRI_SYSTEM_PROMPT}] + user_history

        # 1. Thử OpenRouter Free Models (nếu có OPENROUTER_API_KEY)
        openrouter_client = self._get_openrouter_client()
        if openrouter_client:
            for model in self.settings.openrouter_free_models_list:
                try:
                    logger.info("Trying OpenRouter Free model: %s", model)
                    response = await openrouter_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=1500,
                        temperature=0.7,
                    )
                    if response.choices and response.choices[0].message.content:
                        reply = response.choices[0].message.content.strip()
                        user_history.append({"role": "assistant", "content": reply})
                        logger.info("Got response from OpenRouter model: %s", model)
                        return reply, model.split("/")[-1].replace(":free", "")
                except Exception as e:
                    logger.warning("OpenRouter model %s failed: %s. Trying next...", model, e)

        # 2. Thử B.AI Models (nếu có AI_API_KEY)
        if self.settings.AI_API_KEY:
            bai_models = [self.settings.AI_PRIMARY_MODEL] + self.settings.fallback_models_list
            bai_client = self._get_bai_client()
            for model in bai_models:
                try:
                    logger.info("Trying B.AI model: %s", model)
                    response = await bai_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=1500,
                        temperature=0.7,
                    )
                    if response.choices and response.choices[0].message.content:
                        reply = response.choices[0].message.content.strip()
                        user_history.append({"role": "assistant", "content": reply})
                        logger.info("Got response from B.AI model: %s", model)
                        return reply, model
                except Exception as e:
                    logger.warning("B.AI model %s failed: %s. Trying next...", model, e)

        # 3. Thử Free AI Engine (Pollinations 'openai-fast' - 100% miễn phí, 0 key)
        try:
            logger.info("Trying Pollinations Free AI Engine (openai-fast)...")
            free_client = AsyncOpenAI(
                base_url="https://text.pollinations.ai/openai",
                api_key="none",
                timeout=25.0
            )
            free_response = await free_client.chat.completions.create(
                model="openai-fast",
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            if free_response.choices and free_response.choices[0].message.content:
                reply = free_response.choices[0].message.content.strip()
                user_history.append({"role": "assistant", "content": reply})
                logger.info("Got response from Pollinations Free AI Engine!")
                return reply, "Airi-Flash"
        except Exception as free_err:
            logger.warning("Pollinations Free AI Engine failed: %s", free_err)

        # 4. Fallback an toàn nếu toàn bộ mạng/engine gặp sự cố
        logger.error("All AI models in cascade failed.")
        fallback_reply = (
            f"Chào bạn, mình là **Airi Sensei**! 🌸\n\n"
            f"Mình đã nhận được câu hỏi của bạn: *\"{message}\"*\n\n"
            f"Hiện tại kết nối AI đang bận hoặc đang bảo trì một chút. "
            f"Bạn hãy thử lại sau giây lát nhé!"
        )
        return fallback_reply, "fallback-persona"
