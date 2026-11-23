from contextlib import suppress
from html import escape

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from filters.common import IsAdmin
from filters.callback.subscription_manager import SubscriptionCallback
from keyboard.inline.subscription_manager import (
    SubscriptionListKeyboard,
    SubscriptionDetailKeyboard,
    SubscriptionConfirmKeyboard,
)
from keyboard.reply import BackKeyboard
from states.admin.subscription_manager import SubscriptionState
from database.models import Subscription
from utils.formatters import build_sub_detail, build_subscriptions_list

router = Router()


@router.callback_query(SubscriptionCallback.filter(F.action == "list"), IsAdmin())
async def subscription_list_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    total = await Subscription.all().count()
    active = await Subscription.filter(is_active=True).count()
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=build_subscriptions_list(total, active),
            reply_markup=await SubscriptionListKeyboard.make(),
        )
    await callback.answer()


@router.callback_query(SubscriptionCallback.filter(F.action == "select"), IsAdmin())
async def subscription_select_callback(
    callback: CallbackQuery,
    callback_data: SubscriptionCallback,
) -> None:
    sub = await Subscription.get_or_none(id=callback_data.subscription_id)
    if not sub:
        await callback.answer(text=_("Subscription not found."), show_alert=True)
        return

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=build_sub_detail(sub),
            reply_markup=SubscriptionDetailKeyboard.make(str(sub.id), sub.is_active),
        )
    await callback.answer()


@router.callback_query(SubscriptionCallback.filter(F.action == "confirm_toggle_active"), IsAdmin())
async def subscription_toggle_active_callback(
    callback: CallbackQuery,
    callback_data: SubscriptionCallback,
) -> None:
    sub = await Subscription.get_or_none(id=callback_data.subscription_id)
    if not sub:
        await callback.answer(text=_("Subscription not found."), show_alert=True)
        return

    action_text = _("deactivate") if sub.is_active else _("activate")
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=_("Are you sure you want to %(action)s %(title)s?") % dict(action=action_text, title=escape(sub.title)),
            reply_markup=SubscriptionConfirmKeyboard.toggle_active(str(sub.id)),
        )
    await callback.answer()


@router.callback_query(SubscriptionCallback.filter(F.action == "do_toggle_active"), IsAdmin())
async def subscription_do_toggle_active_callback(
    callback: CallbackQuery,
    callback_data: SubscriptionCallback,
) -> None:
    sub = await Subscription.get_or_none(id=callback_data.subscription_id)
    if not sub:
        await callback.answer(text=_("Subscription not found."), show_alert=True)
        return

    sub.is_active = not sub.is_active
    await sub.save()

    await callback.message.edit_text(
        text=build_sub_detail(sub),
        reply_markup=SubscriptionDetailKeyboard.make(str(sub.id), sub.is_active),
    )
    await callback.answer(
        text=_("Subscription activated.") if sub.is_active else _("Subscription deactivated.")
    )


@router.callback_query(SubscriptionCallback.filter(F.action == "confirm_delete"), IsAdmin())
async def subscription_confirm_delete_callback(
    callback: CallbackQuery,
    callback_data: SubscriptionCallback,
) -> None:
    sub = await Subscription.get_or_none(id=callback_data.subscription_id)
    if not sub:
        await callback.answer(text=_("Subscription not found."), show_alert=True)
        return

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=_("Are you sure you want to delete %(title)s?") % dict(title=escape(sub.title)),
            reply_markup=SubscriptionConfirmKeyboard.delete(str(sub.id)),
        )
    await callback.answer()


@router.callback_query(SubscriptionCallback.filter(F.action == "do_delete"), IsAdmin())
async def subscription_do_delete_callback(
    callback: CallbackQuery,
    callback_data: SubscriptionCallback,
) -> None:
    sub = await Subscription.get_or_none(id=callback_data.subscription_id)
    if sub:
        await sub.delete()

    total = await Subscription.all().count()
    active = await Subscription.filter(is_active=True).count()
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=build_subscriptions_list(total, active),
            reply_markup=await SubscriptionListKeyboard.make(),
        )
    await callback.answer(text=_("Subscription deleted."))


@router.callback_query(SubscriptionCallback.filter(F.action == "add"), IsAdmin())
async def subscription_add_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(SubscriptionState.WAITING_FOR_CHAT)
    await callback.message.answer(
        text=_("Use the Back button to cancel at any time."),
        reply_markup=BackKeyboard.make(),
    )
    await callback.message.answer(
        text=_(
            "<b>Step 1 — Channel or group</b>\n"
            "\n"
            "Send the channel or group <b>ID</b>, <b>@username</b>,\n"
            "or <b>forward any message</b> from it.\n"
            "\n"
            "The bot must be an <b>administrator</b> in the channel or group."
        ),
    )
    await callback.answer()
