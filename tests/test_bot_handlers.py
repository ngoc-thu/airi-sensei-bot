import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, Chat
from telegram.constants import ChatType
from app.agent.agent import AgentResult
from app.bot.handlers import (
    start_command,
    clear_command,
    image_command,
    detect_image_prompt,
    auth_command,
    help_command,
    models_command,
    status_command,
    text_message_handler,
)


@pytest.fixture
def mock_update():
    user = User(id=123, first_name="Tien", is_bot=False)
    chat = Chat(id=456, type=ChatType.PRIVATE)
    message = MagicMock(spec=Message)
    message.from_user = user
    message.chat = chat
    message.text = "/start"
    message.reply_text = AsyncMock()
    message.reply_photo = AsyncMock()
    message.reply_chat_action = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.args = []
    context.bot.send_chat_action = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    await start_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Airi Sensei" in call_args


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    await help_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "HƯỚNG DẪN" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_models_command(mock_update, mock_context):
    with patch("app.bot.handlers.auth_service.is_authorized", return_value=True):
        await models_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        assert "OpenRouter" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_status_command(mock_update, mock_context):
    await status_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "Online 24/7" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_auth_command_success(mock_update, mock_context):
    mock_context.args = ["airi2026"]
    with patch("app.bot.handlers.auth_service.authenticate", return_value=True):
        await auth_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        assert "thành công" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_auth_command_fail(mock_update, mock_context):
    mock_context.args = ["wrong_pass"]
    with patch("app.bot.handlers.auth_service.authenticate", return_value=False):
        await auth_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        assert "không đúng" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_clear_command_authorized(mock_update, mock_context):
    with patch("app.bot.handlers.auth_service.is_authorized", return_value=True):
        with patch("app.bot.handlers.chat_service") as mock_chat:
            with patch("app.bot.handlers.airi_agent") as mock_agent:
                await clear_command(mock_update, mock_context)
                mock_chat.clear_history.assert_called_once_with(123)
                mock_agent.clear_history.assert_called_once_with(123)
                mock_update.message.reply_text.assert_called_once()
                assert "làm mới" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_clear_command_unauthorized(mock_update, mock_context):
    with patch("app.bot.handlers.auth_service.is_authorized", return_value=False):
        await clear_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        assert "Truy cập bị từ chối" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_text_message_handler_with_agent(mock_update, mock_context):
    mock_update.message.text = "Thời tiết hôm nay thế nào?"
    agent_result = AgentResult(
        text="Hôm nay trời nắng đẹp!",
        images=[],
        tools_used=["web_search"]
    )
    with patch("app.bot.handlers.auth_service.is_authorized", return_value=True):
        with patch("app.bot.handlers.airi_agent.run", new_callable=AsyncMock, return_value=agent_result):
            await text_message_handler(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            call_text = mock_update.message.reply_text.call_args[0][0]
            assert "Hôm nay trời nắng đẹp!" in call_text
            assert "web_search" in call_text


@pytest.mark.asyncio
async def test_text_message_handler_with_agent_image(mock_update, mock_context):
    mock_update.message.text = "Vẽ một chú mèo"
    fake_img_bytes = b"fake_png_data"
    agent_result = AgentResult(
        text="Đây là bức tranh chú mèo!",
        images=[(fake_img_bytes, "a cute cat")],
        tools_used=["generate_image"]
    )
    with patch("app.bot.handlers.auth_service.is_authorized", return_value=True):
        with patch("app.bot.handlers.airi_agent.run", new_callable=AsyncMock, return_value=agent_result):
            await text_message_handler(mock_update, mock_context)
            mock_update.message.reply_photo.assert_called_once()
            mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_text_message_handler_group_ignored(mock_update, mock_context):
    group_chat = Chat(id=456, type=ChatType.GROUP)
    mock_update.effective_chat = group_chat
    mock_update.message.chat = group_chat
    mock_update.message.text = "Chào mọi người trong nhóm"
    mock_update.message.reply_to_message = None
    mock_update.message.entities = []
    mock_context.bot.username = "AiriSenseiBot"

    await text_message_handler(mock_update, mock_context)
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_text_message_handler_group_mention_only(mock_update, mock_context):
    supergroup_chat = Chat(id=456, type=ChatType.SUPERGROUP)
    mock_update.effective_chat = supergroup_chat
    mock_update.message.chat = supergroup_chat
    mock_update.message.text = "@AiriSenseiBot"
    mock_update.message.reply_to_message = None
    mock_update.message.entities = []
    mock_context.bot.username = "AiriSenseiBot"

    with patch("app.bot.handlers.auth_service.is_authorized", return_value=True):
        await text_message_handler(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        assert "Airi nghe đây" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_text_message_handler_group_with_question(mock_update, mock_context):
    supergroup_chat = Chat(id=456, type=ChatType.SUPERGROUP)
    mock_update.effective_chat = supergroup_chat
    mock_update.message.chat = supergroup_chat
    mock_update.message.text = "@AiriSenseiBot thời tiết hôm nay thế nào?"
    mock_update.message.reply_to_message = None
    mock_update.message.entities = []
    mock_context.bot.username = "AiriSenseiBot"

    agent_result = AgentResult(text="Trời đẹp!", images=[], tools_used=[])
    with patch("app.bot.handlers.auth_service.is_authorized", return_value=True):
        with patch("app.bot.handlers.airi_agent.run", new_callable=AsyncMock, return_value=agent_result) as mock_run:
            await text_message_handler(mock_update, mock_context)
            mock_run.assert_called_once()
            assert mock_run.call_args[1]["user_input"] == "thời tiết hôm nay thế nào?"
            mock_update.message.reply_text.assert_called_once()


def test_detect_image_prompt():
    assert detect_image_prompt("tạo ảnh con mèo") == "con mèo"
    assert detect_image_prompt("vẽ một chú cún con dễ thương") == "một chú cún con dễ thương"
    assert detect_image_prompt("vẽ tranh phong cảnh anime") == "phong cảnh anime"
    assert detect_image_prompt("draw a futuristic robot") == "a futuristic robot"
    assert detect_image_prompt("thời tiết hôm nay thế nào") is None
