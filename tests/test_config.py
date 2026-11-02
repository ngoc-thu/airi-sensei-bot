import os
from unittest.mock import patch
import pytest


def test_settings_load_defaults():
    from app.config import Settings

    with patch.dict(os.environ, {"BOT_TOKEN": "test_token"}, clear=True):
        settings = Settings()
        assert settings.BOT_TOKEN == "test_token"
        assert settings.AI_BASE_URL == "https://api.b.ai/v1"
        assert settings.AI_PRIMARY_MODEL == "deepseek-v4.1-flash"
        assert "qwen3.8-flash" in settings.fallback_models_list
        assert "llama-3.3-70b-versatile" in settings.groq_models_list
        assert settings.PORT == 8080
        assert settings.IMAGE_MODEL == "flux"


def test_settings_custom_env():
    from app.config import Settings

    custom_env = {
        "BOT_TOKEN": "custom_token_123",
        "AI_BASE_URL": "https://custom.ai/v1",
        "AI_API_KEY": "custom_key",
        "AI_PRIMARY_MODEL": "gpt-custom",
        "AI_FALLBACK_MODELS": "model1,model2,model3",
        "PORT": "9000",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, custom_env, clear=True):
        settings = Settings()
        assert settings.BOT_TOKEN == "custom_token_123"
        assert settings.AI_BASE_URL == "https://custom.ai/v1"
        assert settings.AI_API_KEY == "custom_key"
        assert settings.AI_PRIMARY_MODEL == "gpt-custom"
        assert settings.fallback_models_list == ["model1", "model2", "model3"]
        assert settings.PORT == 9000
        assert settings.LOG_LEVEL == "DEBUG"
