import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.config import Settings
from app.ai.chat_service import ChatService


@pytest.fixture
def mock_settings():
    return Settings(
        BOT_TOKEN="mock_bot_token",
        AI_BASE_URL="https://api.b.ai/v1",
        AI_API_KEY="mock_key",
        AI_PRIMARY_MODEL="deepseek-v4.1-flash",
        AI_FALLBACK_MODELS="qwen3.8-flash",
        OPENROUTER_API_KEY="",
    )


@pytest.mark.asyncio
async def test_chat_service_success_primary_model(mock_settings):
    service = ChatService(settings=mock_settings)

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Xin chào! Mình là Airi Sensei."))
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch.object(service, "_get_bai_client", return_value=mock_client):
        reply, model_used = await service.ask(user_id=123, message="Chào bạn")
        assert reply == "Xin chào! Mình là Airi Sensei."
        assert model_used == "deepseek-v4.1-flash"


@pytest.mark.asyncio
async def test_chat_service_fallback_on_first_model_error(mock_settings):
    service = ChatService(settings=mock_settings)

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Câu trả lời từ model fallback Qwen."))
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[Exception("insufficient_user_quota"), mock_response]
    )

    with patch.object(service, "_get_bai_client", return_value=mock_client):
        reply, model_used = await service.ask(user_id=123, message="Hỏi câu hỏi")
        assert reply == "Câu trả lời từ model fallback Qwen."
        assert model_used == "qwen3.8-flash"


@pytest.mark.asyncio
async def test_chat_service_all_models_fail_uses_graceful_fallback(mock_settings):
    service = ChatService(settings=mock_settings)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("All models failed")
    )

    with patch.object(service, "_get_bai_client", return_value=mock_client):
        with patch("app.ai.chat_service.AsyncOpenAI", return_value=mock_client):
            reply, model_used = await service.ask(user_id=123, message="Thời tiết hôm nay thế nào?")
            assert "Airi Sensei" in reply
            assert model_used == "fallback-persona"


def test_chat_service_clear_history(mock_settings):
    service = ChatService(settings=mock_settings)
    service.history[123] = [{"role": "user", "content": "hi"}]
    service.clear_history(123)
    assert 123 not in service.history
