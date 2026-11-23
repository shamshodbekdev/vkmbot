from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from keyboard.inline import StartKeyboard
from utils.constants.subscription import CHECK_SUBSCRIPTIONS_CALLBACK
from utils.helpers import safe_delete

router = Router()


@router.callback_query(F.data == CHECK_SUBSCRIPTIONS_CALLBACK)
async def check_subscriptions_handler(callback: CallbackQuery) -> None:
    # SubscriptionMiddleware lets this through only once the user joined every channel.
    await callback.answer(_("Thank you for subscribing!"))
    await safe_delete(callback.message)
    await callback.message.answer(
        text=_("Hello, world!"),
        reply_markup=StartKeyboard.make(),
    )
