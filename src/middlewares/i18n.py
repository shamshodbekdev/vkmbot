from typing import Any, Dict, Optional

from aiogram.types import TelegramObject
from aiogram.utils.i18n import I18nMiddleware as BaseI18nMiddleware

from database.models import User


class I18nMiddleware(BaseI18nMiddleware):
    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:
        user: Optional[User] = data.get("user")
        if user and user.language_code in self.i18n.available_locales:
            return user.language_code
        return self.i18n.default_locale
