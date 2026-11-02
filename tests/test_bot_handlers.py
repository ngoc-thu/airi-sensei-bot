import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, Chat
from telegram.constants import ChatType
from app.config import Settings
from app.bot.handlers import start_command, clear_command, image_command


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
async def test_clear_command(mock_update, mock_context):
    with patch("app.bot.handlers.chat_service") as mock_chat:
        await clear_command(mock_update, mock_context)
        mock_chat.clear_history.assert_called_once_with(123)
        mock_update.message.reply_text.assert_called_once()
        assert "làm mới" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_image_command_no_prompt(mock_update, mock_context):
    mock_context.args = []
    await image_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "/image" in mock_update.message.reply_text.call_args[0][0]
