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


@pytest.mark.asyncio
async def test_agent_openclaw_tools_execution(mock_settings, tmp_path):
    from app.services.memory_service import MemoryService
    mem = MemoryService(db_path=str(tmp_path / "agent_mem.db"))
    agent = AiriAgent(settings=mock_settings, memory_service=mem)

    # 1. remember_user_fact tool
    mock_tool_1 = MagicMock()
    mock_tool_1.id = "call_fact"
    mock_tool_1.function.name = "remember_user_fact"
    mock_tool_1.function.arguments = '{"key": "tên_gọi", "value": "anh yêu"}'

    resp_1 = MagicMock(choices=[MagicMock(message=MagicMock(content=None, tool_calls=[mock_tool_1]))])
    resp_2 = MagicMock(choices=[MagicMock(message=MagicMock(content="Dạ em nhớ rồi anh yêu ơi!", tool_calls=None))])

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[resp_1, resp_2])

    with patch.object(agent, "_get_client", return_value=mock_client):
        res = await agent.run(user_id=5556841083, user_input="Từ giờ gọi anh là anh yêu nha")
        assert "anh yêu" in res.text
        assert "remember_user_fact" in res.tools_used
        assert len(res.steps) == 1
        assert res.steps[0].tool_name == "remember_user_fact"
        assert mem.get_facts(5556841083)["tên_gọi"] == "anh yêu"


def test_agent_groq_client_creation():
    settings = Settings(
        BOT_TOKEN="mock_token",
        GROQ_API_KEY="gsk_test123",
        GROQ_BASE_URL="https://api.groq.com/openai/v1",
        GROQ_MODELS="openai/gpt-oss-120b",
    )
    agent = AiriAgent(settings=settings)
    client = agent._create_client_for_model("openai/gpt-oss-120b")
    assert "api.groq.com" in str(client.base_url)


def test_agent_gemini_client_creation():
    settings = Settings(
        BOT_TOKEN="mock_token",
        GEMINI_API_KEY="AQ.test123",
        GEMINI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/",
        GEMINI_MODELS="gemini-2.5-flash",
    )
    agent = AiriAgent(settings=settings)
    client = agent._create_client_for_model("gemini-2.5-flash")
    assert "generativelanguage.googleapis.com" in str(client.base_url)
