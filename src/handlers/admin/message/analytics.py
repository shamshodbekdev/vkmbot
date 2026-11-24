from aiogram import F, Router
from aiogram.types import BufferedInputFile, Message
from aiogram.utils.i18n import lazy_gettext as __

from filters.common import IsModerator
from keyboard.inline.reload import ReloadKeyboard
from services.admin_panel_cache import analytics_panel

router = Router()


@router.message(F.text == __("Analytics"), IsModerator())
async def analytics_handler(message: Message) -> None:
    caption, image = await analytics_panel()
    await message.answer_photo(
        photo=BufferedInputFile(image, filename="analytics.png"),
        caption=caption,
        reply_markup=ReloadKeyboard.analytics(),
    )
