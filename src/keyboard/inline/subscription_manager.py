from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _
from filters.callback.subscription_manager import SubscriptionCallback, SubscriptionSetupCallback
from database.models import Subscription
from utils.constants.subscription import SUBSCRIPTION_STATUS, RELOAD_ICON


class SubscriptionListKeyboard:
    @staticmethod
    async def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for sub in await Subscription.all().order_by("created_at"):
            icon = next(i for active, i in SUBSCRIPTION_STATUS if active == sub.is_active)
            builder.row(
                InlineKeyboardButton(
                    text=sub.title,
                    icon_custom_emoji_id=icon,
                    callback_data=SubscriptionCallback(
                        action="select",
                        subscription_id=str(sub.id),
                    ).pack(),
                )
            )
        builder.row(
            InlineKeyboardButton(
                text=_("Add subscription"),
                icon_custom_emoji_id="5226945370684140473",
                callback_data=SubscriptionCallback(action="add").pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()


class SubscriptionDetailKeyboard:
    @staticmethod
    def make(subscription_id: str, is_active: bool) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Reload"),
                icon_custom_emoji_id=RELOAD_ICON,
                callback_data=SubscriptionCallback(
                    action="select",
                    subscription_id=subscription_id,
                ).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Deactivate") if is_active else _("Activate"),
                icon_custom_emoji_id="5465665476971471368" if is_active else "5427009714745517609",
                callback_data=SubscriptionCallback(
                    action="confirm_toggle_active",
                    subscription_id=subscription_id,
                ).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Delete subscription"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=SubscriptionCallback(
                    action="confirm_delete",
                    subscription_id=subscription_id,
                ).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=SubscriptionCallback(action="list").pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()


class SubscriptionConfirmKeyboard:
    @staticmethod
    def toggle_active(subscription_id: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Confirm"),
                icon_custom_emoji_id="5427009714745517609",
                callback_data=SubscriptionCallback(
                    action="do_toggle_active",
                    subscription_id=subscription_id,
                ).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Cancel"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=SubscriptionCallback(
                    action="select",
                    subscription_id=subscription_id,
                ).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def delete(subscription_id: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Confirm"),
                icon_custom_emoji_id="5427009714745517609",
                callback_data=SubscriptionCallback(
                    action="do_delete",
                    subscription_id=subscription_id,
                ).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=_("Cancel"),
                icon_custom_emoji_id="5465665476971471368",
                callback_data=SubscriptionCallback(
                    action="select",
                    subscription_id=subscription_id,
                ).pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()


class SubscriptionInviteLinkKeyboard:
    @staticmethod
    def make() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Create here"),
                icon_custom_emoji_id="5226945370684140473",
                callback_data=SubscriptionSetupCallback(action="create_link").pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()


class SubscriptionMaxAudienceKeyboard:
    @staticmethod
    def make(total_count: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=_("Use max: %(count)s") % dict(count=total_count),
                icon_custom_emoji_id="5424885441100782420",
                callback_data=SubscriptionSetupCallback(action="use_count").pack(),
            )
        )
        builder.adjust(1)
        return builder.as_markup()
