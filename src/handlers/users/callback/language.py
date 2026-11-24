from contextlib import suppress
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n import gettext as _

from database.models import User, UserPreferences
from filters.callback import LanguageCallback
from keyboard.inline import LanguageKeyboard, SettingsKeyboard, StartKeyboard
from middlewares.subscription import not_joined_subscriptions, subscription_prompt
from utils.constants import LANGUAGES
from utils.helpers import mark_language_chosen, safe_delete

router = Router()

_LANGUAGE_CODES = {code for code, _name, _selected in LANGUAGES}


@router.callback_query(LanguageCallback.filter(F.action == "close"))
async def language_close_handler(callback: CallbackQuery) -> None:
    await safe_delete(callback.message)
    await callback.answer()


@router.callback_query(LanguageCallback.filter())
async def language_callback_handler(
    callback: CallbackQuery,
    callback_data: LanguageCallback,
    user: User,
    i18n: I18n,
    bot: Bot,
) -> None:
    if callback_data.language_code not in _LANGUAGE_CODES:
        await callback.answer()
        return

    if user.language_code != callback_data.language_code:
        user.language_code = callback_data.language_code
        await user.save()

    if callback.from_user is not None:
        await mark_language_chosen(callback.from_user.id)

    # Switch the locale for the rest of this update so the reply is already translated.
    i18n.current_locale = user.language_code
    await callback.answer(_("Language updated successfully."))

    if callback_data.action == "start":
        # First visit: next comes the mandatory subscription (if any), then the main menu.
        await safe_delete(callback.message)
        not_joined = await not_joined_subscriptions(bot=bot, user_id=callback.from_user.id)
        if not_joined:
            text, markup = subscription_prompt(not_joined)
            await callback.message.answer(text=text, reply_markup=markup)
        else:
            await callback.message.answer(text=_("Hello, world!"), reply_markup=StartKeyboard.make())
        return

    with suppress(TelegramBadRequest):
        if callback_data.action == "settings":
            prefs, __ = await UserPreferences.get_or_create(user=user)
            await callback.message.edit_text(
                _("<b>Settings</b>\n\nWhat would you like to change?"),
                reply_markup=SettingsKeyboard.make(
                    language_code=user.language_code,
                    max_results=prefs.max_results,
                    like_buttons=prefs.like_buttons,
                ),
            )
        else:
            await callback.message.edit_text(
                _("Choose your language:"),
                reply_markup=LanguageKeyboard.make(user.language_code),
            )
