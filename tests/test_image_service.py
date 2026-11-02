import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.config import Settings
from app.ai.image_service import ImageService


@pytest.fixture
def mock_settings():
    return Settings(
        BOT_TOKEN="mock_bot_token",
        IMAGE_MODEL="flux",
        IMAGE_FALLBACK_MODEL="turbo",
    )


def test_image_service_build_url(mock_settings):
    service = ImageService(settings=mock_settings)
    url = service.build_url("một chú mèo dễ thương", model="flux")
    assert "https://image.pollinations.ai/prompt/" in url
    assert "model=flux" in url
    assert "width=1024" in url
    assert "height=1024" in url


@pytest.mark.asyncio
async def test_image_service_generate_success_primary(mock_settings):
    service = ImageService(settings=mock_settings)
    mock_bytes = b"fake_image_bytes_flux"

    with patch.object(service, "_fetch_image_bytes", AsyncMock(return_value=mock_bytes)):
        image_bytes, model_used = await service.generate_image("a cute cat")
        assert image_bytes == mock_bytes
        assert model_used == "flux"


@pytest.mark.asyncio
async def test_image_service_fallback_on_primary_failure(mock_settings):
    service = ImageService(settings=mock_settings)
    mock_fallback_bytes = b"fake_image_bytes_turbo"

    async def mock_fetch(url):
        if "model=flux" in url:
            raise Exception("Flux timeout")
        return mock_fallback_bytes

    with patch.object(service, "_fetch_image_bytes", side_effect=mock_fetch):
        image_bytes, model_used = await service.generate_image("a cute cat")
        assert image_bytes == mock_fallback_bytes
        assert model_used == "turbo"
