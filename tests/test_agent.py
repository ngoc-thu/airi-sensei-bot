import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.config import Settings
from app.agent.agent import AiriAgent, AgentResult


@pytest.fixture
def mock_settings():
    return Settings(
        BOT_TOKEN="mock_token",
        AI_BASE_URL="https://api.b.ai/v1",
        AI_API_KEY="mock_key",
    )


@pytest.mark.asyncio
async def test_agent_direct_response(mock_settings):
    agent = AiriAgent(settings=mock_settings)

    mock_msg = MagicMock(content="Chào bạn, mình là Airi Sensei!", tool_calls=None)
    mock_choice = MagicMock(message=mock_msg)
    mock_resp = MagicMock(choices=[mock_choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with patch.object(agent, "_get_client", return_value=mock_client):
        result = await agent.run(user_id=123, user_input="Xin chào")
        assert isinstance(result, AgentResult)
        assert "Airi Sensei" in result.text
        assert len(result.tools_used) == 0


@pytest.mark.asyncio
async def test_agent_tool_call_execution(mock_settings):
    agent = AiriAgent(settings=mock_settings)

    # Step 1: Model requests web_search tool
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "get_current_time"
    mock_tool_call.function.arguments = "{}"

    mock_msg_1 = MagicMock(content=None, tool_calls=[mock_tool_call])
    mock_resp_1 = MagicMock(choices=[MagicMock(message=mock_msg_1)])

    # Step 2: Model returns final response using tool output
    mock_msg_2 = MagicMock(content="Hôm nay là Thứ Hai, ngày 02/11/2026.", tool_calls=None)
    mock_resp_2 = MagicMock(choices=[MagicMock(message=mock_msg_2)])

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_resp_1, mock_resp_2])

    with patch.object(agent, "_get_client", return_value=mock_client):
        result = await agent.run(user_id=123, user_input="Bây giờ là mấy giờ?")
        assert "Thứ Hai" in result.text
        assert "get_current_time" in result.tools_used
