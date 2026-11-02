import logging
from typing import Set
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.authorized_users: Set[int] = set(self.settings.allowed_user_ids_list)

    def is_authorized(self, user_id: int) -> bool:
        """
        Kiểm tra người dùng đã được xác thực hay chưa
        """
        if not self.settings.AUTH_ENABLED:
            return True
        return user_id in self.authorized_users

    def authenticate(self, user_id: int, passcode: str) -> bool:
        """
        Xác thực bằng passcode. Nếu đúng thì cấp quyền vĩnh viễn trong runtime.
        """
        if not passcode:
            return False

        if passcode.strip() == self.settings.AUTH_PASSCODE.strip():
            self.authorized_users.add(user_id)
            logger.info("User %s successfully authenticated with passcode", user_id)
            return True

        logger.warning("User %s failed authentication attempt with passcode: %s", user_id, passcode)
        return False
