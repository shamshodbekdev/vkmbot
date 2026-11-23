from contextlib import suppress
from html import escape

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, MessageOriginChannel, MessageOriginChat
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.utils.i18n import gettext as _, lazy_gettext as __
from filters.common import IsAdmin
from filters.callback.subscription_manager import SubscriptionSetupCallback
from keyboard.inline.subscription_manager import (
    SubscriptionListKeyboard,
    SubscriptionDetailKeyboard,
    SubscriptionInviteLinkKeyboard,
    SubscriptionMaxAudienceKeyboard,
)
from keyboard.reply import BackKeyboard, ManageKeyboard
from states.admin.subscription_manager import SubscriptionState
from database.models import Subscription, User
from utils.formatters import build_subscriptions_list

router = Router()


async def _strip_inline(bot: Bot, chat_id: int, message_id: int) -> None:
    with suppress(TelegramAPIError):
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=None,
        )


@router.message(F.text == __("Mandatory subscription"), IsAdmin())
async def subscription_manager_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    total = await Subscription.all().count()
    active = await Subscription.filter(is_active=True).count()
    await message.answer(
        text=build_subscriptions_list(total, active),
        reply_markup=await SubscriptionListKeyboard.make(),
    )


@router.message(F.text == "⬅️", StateFilter(SubscriptionState), IsAdmin())
async def subscription_manager_back_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    inline_message_id = data.get("inline_message_id")
    await state.clear()
    if inline_message_id:
        await _strip_inline(message.bot, message.chat.id, inline_message_id)
    await message.answer(
        text=_("Main menu"),
        reply_markup=ManageKeyboard.make(),
    )


@router.message(StateFilter(SubscriptionState.WAITING_FOR_CHAT), IsAdmin())
async def subscription_chat_handler(message: Message, state: FSMContext) -> None:
    chat = None

    origin = message.forward_origin
    if isinstance(origin, MessageOriginChannel):
        chat = origin.chat
    elif isinstance(origin, MessageOriginChat):
        chat = origin.sender_chat
    elif message.text:
        identifier = message.text.strip()
        try:
            chat = await message.bot.get_chat(
                identifier if identifier.startswith("@") else int(identifier)
            )
        except Exception:
            await message.answer(
                text=_("Channel or group not found. Please try again."),
            )
            return
    else:
        await message.answer(
            text=_("Please send a chat ID, @username, or forward a message from the channel or group."),
        )
        return

    try:
        bot_member = await message.bot.get_chat_member(chat.id, message.bot.id)
        if bot_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
            await message.answer(
                text=_("Bot is not an administrator in <b>%(title)s</b>. Please add the bot as admin and try again.") % dict(title=escape(chat.title or str(chat.id))),
            )
            return
    except Exception:
        await message.answer(
            text=_("Failed to verify bot permissions. Make sure the bot is an administrator."),
        )
        return

    try:
        member_count = await message.bot.get_chat_member_count(chat.id)
    except Exception:
        member_count = 0

    await state.update_data(
        sub_chat_id=chat.id,
        sub_title=(chat.title or str(chat.id))[:255],
        sub_chat_type=chat.type if isinstance(chat.type, str) else chat.type.value,
        sub_member_count=member_count,
    )
    await state.set_state(SubscriptionState.WAITING_FOR_INVITE_LINK)

    sent = await message.answer(
        text=_(
            "<b>Step 2 — Invite link</b>\n"
            "\n"
            "Send an invite link for <b>%(title)s</b>,\n"
            "or tap <b>Create here</b> to generate one automatically."
        ) % dict(title=escape(chat.title or str(chat.id))),
        reply_markup=SubscriptionInviteLinkKeyboard.make(),
    )
    await state.update_data(inline_message_id=sent.message_id)


@router.callback_query(
    SubscriptionSetupCallback.filter(F.action == "create_link"),
    SubscriptionState.WAITING_FOR_INVITE_LINK,
    IsAdmin(),
)
async def subscription_create_link_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    chat_id = data["sub_chat_id"]
    try:
        link_obj = await callback.bot.create_chat_invite_link(chat_id)
        invite_link = link_obj.invite_link
    except Exception:
        await callback.answer(
            text=_("Failed to create invite link. Check bot permissions."),
            show_alert=True,
        )
        return
    await _go_to_max_audience(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        reply_target=callback.message,
        state=state,
        data=data,
        invite_link=invite_link,
    )
    await callback.answer()


@router.message(StateFilter(SubscriptionState.WAITING_FOR_INVITE_LINK), IsAdmin())
async def subscription_invite_link_handler(message: Message, state: FSMContext) -> None:
    link = message.text.strip() if message.text else None
    if not link or not link.startswith(("https://", "http://")) or len(link) > 255:
        await message.answer(
            text=_("Please send a valid invite link starting with https://."),
        )
        return
    data = await state.get_data()
    await _go_to_max_audience(
        bot=message.bot,
        chat_id=message.chat.id,
        reply_target=message,
        state=state,
        data=data,
        invite_link=link,
    )


async def _go_to_max_audience(
    bot: Bot,
    chat_id: int,
    reply_target,
    state: FSMContext,
    data: dict,
    invite_link: str,
) -> None:
    inline_message_id = data.get("inline_message_id")
    if inline_message_id:
        await _strip_inline(bot, chat_id, inline_message_id)

    await state.update_data(sub_invite_link=invite_link)
    await state.set_state(SubscriptionState.WAITING_FOR_MAX_AUDIENCE)

    user_count = await User.all().count()
    sent = await reply_target.answer(
        text=_(
            "<b>Step 3 — Maximum audience</b>\n"
            "\n"
            "How many users can join via this link?\n"
            "Send a number or tap <b>Use max: %(count)s</b> to use total registered users."
        ) % dict(count=user_count),
        reply_markup=SubscriptionMaxAudienceKeyboard.make(user_count),
    )
    await state.update_data(inline_message_id=sent.message_id)


@router.callback_query(
    SubscriptionSetupCallback.filter(F.action == "use_count"),
    SubscriptionState.WAITING_FOR_MAX_AUDIENCE,
    IsAdmin(),
)
async def subscription_use_count_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    await _save_subscription(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        reply_target=callback.message,
        state=state,
        data=data,
        max_audience=await User.all().count(),
    )
    await callback.answer()


@router.message(StateFilter(SubscriptionState.WAITING_FOR_MAX_AUDIENCE), IsAdmin())
async def subscription_max_audience_handler(message: Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else None
    if not text or not text.isdigit() or int(text) <= 0:
        await message.answer(
            text=_("Please send a valid positive number."),
        )
        return
    data = await state.get_data()
    await _save_subscription(
        bot=message.bot,
        chat_id=message.chat.id,
        reply_target=message,
        state=state,
        data=data,
        max_audience=int(text),
    )


async def _save_subscription(
    bot: Bot,
    chat_id: int,
    reply_target,
    state: FSMContext,
    data: dict,
    max_audience: int,
) -> None:
    inline_message_id = data.get("inline_message_id")
    if inline_message_id:
        await _strip_inline(bot, chat_id, inline_message_id)

    sub = await Subscription.create(
        chat_id=data["sub_chat_id"],
        title=data["sub_title"],
        chat_type=ChatType(data["sub_chat_type"]),
        invite_link=data["sub_invite_link"],
        maximum_audience=max_audience,
    )
    await state.clear()

    await reply_target.answer(
        text=_("Main menu"),
        reply_markup=ManageKeyboard.make(),
    )
    await reply_target.answer(
        text=_(
            "<b>%(title)s</b>\n"
            "\n"
            "Subscription added successfully."
        ) % dict(title=escape(sub.title)),
        reply_markup=SubscriptionDetailKeyboard.make(str(sub.id), sub.is_active),
    )
