from contextlib import suppress
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _
from keyboard.inline import ManageUserKeyboard
from filters.callback import UserManageCallback
from filters.common import IsAdmin
from database.models import User
from utils.helpers import is_temp_banned
from utils.formatters import build_user_detail
import datetime

router = Router()
UTC = datetime.timezone.utc


@router.callback_query(UserManageCallback.filter(F.action == "reload"), IsAdmin())
async def user_reload_callback(callback: CallbackQuery, callback_data: UserManageCallback) -> None:
    user = await User.get_or_none(telegram_id=callback_data.user_id)
    if user is None:
        await callback.answer(_("User not found."), show_alert=True)
        return
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=build_user_detail(user),
            reply_markup=ManageUserKeyboard.detail(user.telegram_id, user.is_blocked, is_temp_banned(user)),
        )
    await callback.answer()


@router.callback_query(UserManageCallback.filter(F.action == "confirm_toggle_block"), IsAdmin())
async def user_confirm_toggle_block_callback(callback: CallbackQuery, callback_data: UserManageCallback) -> None:
    user = await User.get_or_none(telegram_id=callback_data.user_id)
    if user is None:
        await callback.answer(_("User not found."), show_alert=True)
        return
    action_text = _("unblock") if user.is_blocked else _("block")
    await callback.message.edit_reply_markup(
        reply_markup=ManageUserKeyboard.confirm_toggle_block(callback_data.user_id, user.is_blocked)
    )
    await callback.answer(
        text=_("Are you sure you want to %(action)s this user?") % dict(action=action_text),
        show_alert=True,
    )


@router.callback_query(UserManageCallback.filter(F.action == "do_toggle_block"), IsAdmin())
async def user_do_toggle_block_callback(callback: CallbackQuery, callback_data: UserManageCallback) -> None:
    user = await User.get_or_none(telegram_id=callback_data.user_id)
    if user is None:
        await callback.answer(_("User not found."), show_alert=True)
        return
    user.is_blocked = not user.is_blocked
    await user.save()
    await callback.message.edit_text(
        text=build_user_detail(user),
        reply_markup=ManageUserKeyboard.detail(user.telegram_id, user.is_blocked, is_temp_banned(user)),
    )
    await callback.answer(
        text=_("User has been blocked successfully.") if user.is_blocked else _("User has been unblocked successfully.")
    )


@router.callback_query(UserManageCallback.filter(F.action == "confirm_temp_ban"), IsAdmin())
async def user_confirm_temp_ban_callback(callback: CallbackQuery, callback_data: UserManageCallback) -> None:
    user = await User.get_or_none(telegram_id=callback_data.user_id)
    if user is None:
        await callback.answer(_("User not found."), show_alert=True)
        return
    await callback.message.edit_reply_markup(
        reply_markup=ManageUserKeyboard.temp_ban_durations(callback_data.user_id, is_temp_banned(user))
    )
    await callback.answer(
        text=_("Select how long to ban this user."),
        show_alert=True,
    )


@router.callback_query(UserManageCallback.filter(F.action == "do_temp_ban"), IsAdmin())
async def user_do_temp_ban_callback(callback: CallbackQuery, callback_data: UserManageCallback) -> None:
    user = await User.get_or_none(telegram_id=callback_data.user_id)
    if user is None:
        await callback.answer(_("User not found."), show_alert=True)
        return
    duration = callback_data.duration or 3600
    user.blocked_until = datetime.datetime.now(UTC) + datetime.timedelta(seconds=duration)
    await user.save()
    await callback.message.edit_text(
        text=build_user_detail(user),
        reply_markup=ManageUserKeyboard.detail(user.telegram_id, user.is_blocked, is_temp_banned(user)),
    )
    await callback.answer(
        text=_("User has been temporarily banned."),
        show_alert=True,
    )


@router.callback_query(UserManageCallback.filter(F.action == "do_clear_ban"), IsAdmin())
async def user_do_clear_ban_callback(callback: CallbackQuery, callback_data: UserManageCallback) -> None:
    user = await User.get_or_none(telegram_id=callback_data.user_id)
    if user is None:
        await callback.answer(_("User not found."), show_alert=True)
        return
    user.blocked_until = None
    await user.save()
    await callback.message.edit_text(
        text=build_user_detail(user),
        reply_markup=ManageUserKeyboard.detail(user.telegram_id, user.is_blocked, False),
    )
    await callback.answer(text=_("Temporary ban cleared."))

