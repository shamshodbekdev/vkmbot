from aiogram import F, Router
from aiogram.types import BufferedInputFile, Message
from aiogram.utils.i18n import lazy_gettext as __

from filters.common import IsModerator
from keyboard.inline.reload import ReloadKeyboard
from services.admin_panel_cache import statistics_panel

router = Router()


@router.message(F.text == __("Statistics"), IsModerator())
async def statistics_handler(message: Message) -> None:
    caption, image = await statistics_panel()
    await message.answer_photo(
        photo=BufferedInputFile(image, filename="statistics.png"),
        caption=caption,
        reply_markup=ReloadKeyboard.statistics(),
    )
