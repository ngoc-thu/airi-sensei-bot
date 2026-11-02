from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram
    BOT_TOKEN: str

    # AI Configuration (B.AI / OpenAI compatible)
    AI_BASE_URL: str = "https://api.b.ai/v1"
    AI_API_KEY: str = ""
    AI_PRIMARY_MODEL: str = "deepseek-v4.1-flash"
    AI_FALLBACK_MODELS: str = "qwen3.8-flash,glm-5.3-flash,minimax-m3.1-flash"

    # Security / Authentication
    AUTH_ENABLED: bool = True
    AUTH_PASSCODE: str = "airi2026"
    ALLOWED_USER_IDS: str = "5556841083"

    # Groq Cloud (Free 14,400 RPD, ultra-fast 500 T/s, native tool calling)
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODELS: str = "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b"

    # Google Gemini API (Free 1,500 RPD, 1M context, high reasoning)
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_MODELS: str = "gemini-3.5-flash,gemini-2.5-flash,gemini-flash-latest"

    # OpenRouter Free Tier
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_FREE_MODELS: str = (
        "nvidia/nemotron-3.5-lightning:free,cohere/north-mini-code:free,google/gemma-4-31b-it:free"
    )

    # Image Generation
    IMAGE_MODEL: str = "flux"
    IMAGE_FALLBACK_MODEL: str = "turbo"

    # Server / Render
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"
    KEEP_ALIVE_URL: Optional[str] = None

    @property
    def allowed_user_ids_list(self) -> List[int]:
        if not self.ALLOWED_USER_IDS:
            return []
        ids = []
        for x in self.ALLOWED_USER_IDS.split(","):
            cleaned = x.strip()
            if cleaned.isdigit():
                ids.append(int(cleaned))
        return ids

    @property
    def groq_models_list(self) -> List[str]:
        if not self.GROQ_MODELS:
            return []
        return [m.strip() for m in self.GROQ_MODELS.split(",") if m.strip()]

    @property
    def gemini_models_list(self) -> List[str]:
        if not self.GEMINI_MODELS:
            return []
        return [m.strip() for m in self.GEMINI_MODELS.split(",") if m.strip()]

    @property
    def fallback_models_list(self) -> List[str]:
        if not self.AI_FALLBACK_MODELS:
            return []
        return [m.strip() for m in self.AI_FALLBACK_MODELS.split(",") if m.strip()]

    @property
    def openrouter_free_models_list(self) -> List[str]:
        if not self.OPENROUTER_FREE_MODELS:
            return []
        return [m.strip() for m in self.OPENROUTER_FREE_MODELS.split(",") if m.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
