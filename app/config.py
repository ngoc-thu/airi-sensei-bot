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

    # OpenRouter Free Tier
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_FREE_MODELS: str = "google/gemma-4-31b-it:free,nvidia/nemotron-3.5-lightning:free,google/gemma-4-26b-a4b-it:free"

    # Image Generation
    IMAGE_MODEL: str = "flux"
    IMAGE_FALLBACK_MODEL: str = "turbo"

    # Server / Render
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"
    KEEP_ALIVE_URL: Optional[str] = None

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
