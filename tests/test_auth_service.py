import pytest
from app.config import Settings
from app.services.auth_service import AuthService


@pytest.fixture
def mock_settings():
    return Settings(
        BOT_TOKEN="mock_token",
        AUTH_ENABLED=True,
        AUTH_PASSCODE="secret123",
        ALLOWED_USER_IDS="111,222",
    )


def test_auth_service_preconfigured_ids(mock_settings):
    auth = AuthService(settings=mock_settings)
    assert auth.is_authorized(111) is True
    assert auth.is_authorized(222) is True
    assert auth.is_authorized(333) is False


def test_auth_service_authenticate_passcode(mock_settings):
    auth = AuthService(settings=mock_settings)
    assert auth.is_authorized(999) is False

    # Wrong passcode
    assert auth.authenticate(999, "wrongpass") is False
    assert auth.is_authorized(999) is False

    # Correct passcode
    assert auth.authenticate(999, "secret123") is True
    assert auth.is_authorized(999) is True


def test_auth_service_disabled():
    settings = Settings(BOT_TOKEN="mock_token", AUTH_ENABLED=False)
    auth = AuthService(settings=settings)
    assert auth.is_authorized(999) is True
