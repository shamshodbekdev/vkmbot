import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Update
from aiogram.utils.i18n import gettext as _
from tortoise.expressions import F

from core.cache import cache
from core.config import config
from database.enums import STAFF_ROLES, UserRole
from database.models import Subscription, SubscriptionTracker, User
from filters.callback.language import LanguageCallback
from keyboard.inline.subscription_check import SubscriptionCheckKeyboard
from utils.constants.subscription import CHECK_SUBSCRIPTIONS_CALLBACK, SUBSCRIPTION_OK_TTL
from utils.helpers.language_choice import has_chosen_language

logger = logging.getLogger(__name__)

NOT_JOINED_STATUSES = (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
_LANGUAGE_CALLBACK_PREFIX = LanguageCallback.__prefix__ + ":"


def subscription_prompt(not_joined: List[Subscription], check_callback: str = CHECK_SUBSCRIPTIONS_CALLBACK):
    """Text and keyboard asking the user to join the channels in ``not_joined``."""
    text = _("Please subscribe to our channels below, then you can use the bot.")
    markup: InlineKeyboardMarkup = SubscriptionCheckKeyboard.make(subscriptions=not_joined, check_callback=check_callback)
    return text, markup


async def not_joined_subscriptions(bot: Bot, user_id: int) -> List[Subscription]:
    """Active mandatory channels the user has not joined (checked with get_chat_member)."""
    return await SubscriptionMiddleware._not_joined(bot=bot, user_id=user_id)


class SubscriptionMiddleware(BaseMiddleware):
    """Requires private-chat users to join every active mandatory channel/group."""

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user: Optional[User] = data.get("user")
        if (
            user is None
            or user.chat_type != ChatType.PRIVATE
            or user.telegram_id == config.telegram_id
            or user.role in STAFF_ROLES
        ):
            return await handler(event, data)

        message = event.message
        callback = event.callback_query
        if message is None and callback is None:
            return await handler(event, data)
        if message is not None and message.chat.type != ChatType.PRIVATE:
            return await handler(event, data)

        # The language is chosen first, so the subscription request is shown in it:
        # let the language buttons through, and /start while no language is chosen.
        if callback is not None and (callback.data or "").startswith(_LANGUAGE_CALLBACK_PREFIX):
            return await handler(event, data)
        if (
            message is not None
            and (message.text or "").startswith("/start")
            and not await has_chosen_language(user.telegram_id)
        ):
            return await handler(event, data)

        ok_key = "subscription_ok:%d" % user.telegram_id
        try:
            if await cache.get(ok_key):
                return await handler(event, data)
        except Exception:
            logger.exception("Subscription cache read failed")

        not_joined = await self._not_joined(bot=data["bot"], user_id=user.telegram_id)
        if not not_joined:
            try:
                await cache.set(ok_key, True, ttl=SUBSCRIPTION_OK_TTL)
            except Exception:
                logger.exception("Subscription cache write failed")
            return await handler(event, data)

        check_callback = callback.data if callback and callback.data else CHECK_SUBSCRIPTIONS_CALLBACK
        text, markup = subscription_prompt(not_joined, check_callback)

        if callback is not None:
            await callback.answer(
                text=_("You are not subscribed to all required channels."),
                show_alert=True,
            )
            if callback.message is not None:
                try:
                    await callback.message.edit_text(text=text, reply_markup=markup)
                except TelegramBadRequest:
                    await callback.message.answer(text=text, reply_markup=markup)
        else:
            await message.reply(text=text, reply_markup=markup)
        return None

    @staticmethod
    async def _not_joined(bot: Bot, user_id: int) -> List[Subscription]:
        not_joined: List[Subscription] = []
        for subscription in await Subscription.filter(is_active=True).order_by("created_at"):
            if (
                subscription.maximum_audience is not None
                and subscription.joined_count >= subscription.maximum_audience
            ):
                continue
            try:
                member = await bot.get_chat_member(chat_id=subscription.chat_id, user_id=user_id)
            except Exception as error:
                # The bot lost access to the chat: do not lock users out because of it.
                logger.warning("Cannot check subscription %s: %s", subscription.chat_id, error)
                continue

            if member.status in NOT_JOINED_STATUSES:
                not_joined.append(subscription)
                continue

            _tracker, created = await SubscriptionTracker.get_or_create(
                user_id=user_id,
                subscription=subscription,
                defaults=dict(is_joined=True),
            )
            if created:
                await Subscription.filter(id=subscription.id).update(joined_count=F("joined_count") + 1)
                if subscription.maximum_audience is not None:
                    await Subscription.filter(
                        id=subscription.id,
                        joined_count__gte=subscription.maximum_audience,
                    ).update(is_active=False)
        return not_joined
