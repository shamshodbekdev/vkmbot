from contextlib import suppress
import datetime
import uuid
from typing import List, Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _, lazy_gettext as __
from filters.common import IsAdmin
from filters.callback.broadcast_language import BroadcastLanguageCallback
from filters.callback.broadcast_chat_type import BroadcastChatTypeCallback
from filters.callback.broadcast_delay import BroadcastDelayCallback
from filters.callback.broadcast_mode import BroadcastModeCallback
from filters.callback.broadcast_confirm import BroadcastConfirmCallback
from filters.callback.broadcast_progress import BroadcastProgressCallback
from filters.callback.broadcast_premium import BroadcastPremiumCallback
from filters.callback.broadcast_history import BroadcastHistoryCallback
from database.models import User
from keyboard.inline.broadcast_language import BroadcastLanguageKeyboard
from keyboard.inline.broadcast_chat_type import BroadcastChatTypeKeyboard
from keyboard.inline.broadcast_delay import BroadcastDelayKeyboard
from keyboard.inline.broadcast_mode import BroadcastModeKeyboard
from keyboard.inline.broadcast_confirm import BroadcastConfirmKeyboard
from keyboard.inline.broadcast_progress import BroadcastProgressKeyboard
from keyboard.inline.broadcast_premium import BroadcastPremiumKeyboard
from keyboard.inline.broadcast_history import BroadcastHistoryKeyboard
from utils.formatters import build_broadcast_summary, build_broadcast_started, build_broadcast_progress
from keyboard.reply import BackKeyboard, ManageKeyboard
from states.admin.broadcast import BroadcastState
from services.broadcast.broadcast import BroadcastService
from services.broadcast.enums import BroadcastMode
from core.scheduler import scheduler
from utils.constants.broadcast import BROADCAST_DELAYS, BROADCAST_TIMEZONE, MAX_SCHEDULE_DAYS
from zoneinfo import ZoneInfo

router = Router()
_LOCAL_TZ = ZoneInfo(BROADCAST_TIMEZONE)
_DATETIME_FORMAT = "%d.%m.%Y %H:%M"


def _delay_label(delay_seconds: int, run_at: Optional[str] = None) -> str:
    if run_at:
        local = datetime.datetime.fromisoformat(run_at).astimezone(_LOCAL_TZ)
        return "%s (%s)" % (local.strftime(_DATETIME_FORMAT), _("Tashkent time"))
    label = next((label for seconds, label in BROADCAST_DELAYS if seconds == delay_seconds), BROADCAST_DELAYS[0][1])
    return _(label)


def _step5_text() -> str:
    return _(
        "<b>Step 5 of 5 — Broadcast message</b>\n"
        "\n"
        "Send the message you want to broadcast to the selected audience.\n"
        "\n"
        "Supported types: text, photo, video, audio, document, sticker, voice, animation, and more.\n"
        "The message will be delivered exactly as you send it.\n"
        "\n"
        "Send your message now."
    )


def _mode_label(mode: str) -> str:
    return _("Forward") if BroadcastMode(mode) == BroadcastMode.FORWARD else _("Copy")


@router.message(F.text == __("Broadcast message"), IsAdmin())
async def broadcast_start_handler(message: Message, state: FSMContext) -> None:
    await message.answer(
        text=_("<b>Broadcast</b>\n\nSelect an action."),
        reply_markup=BroadcastHistoryKeyboard.menu(),
    )


@router.callback_query(BroadcastHistoryCallback.filter(F.action == "new"), IsAdmin())
async def broadcast_new_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastState.WAITING_FOR_LANGUAGES)
    await state.update_data(languages=[])
    await callback.message.answer(
        text=_("Broadcast mode activated. Use the Back button to cancel at any time."),
        reply_markup=BackKeyboard.make(),
    )
    sent = await callback.message.answer(
        text=_(
            "<b>Step 1 of 5 — Target languages</b>\n"
            "\n"
            "Select the languages of the users you want to reach.\n"
            "Only users whose interface language matches one of the selected options will receive the broadcast.\n"
            "\n"
            "You can select multiple languages. Tap a language to toggle it, then press <b>Continue</b>."
        ),
        reply_markup=BroadcastLanguageKeyboard.make(selected=[]),
    )
    await state.update_data(inline_message_id=sent.message_id)
    await callback.answer()


@router.message(
    F.text == "⬅️",
    StateFilter(BroadcastState),
    IsAdmin(),
)
async def broadcast_back_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    inline_message_id = data.get("inline_message_id")
    await state.clear()
    if inline_message_id:
        with suppress(TelegramAPIError):
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=inline_message_id,
                reply_markup=None,
            )
    await message.answer(
        text=_("Broadcast cancelled. Returning to main menu."),
        reply_markup=ManageKeyboard.make(),
    )


@router.callback_query(
    BroadcastLanguageCallback.filter(F.action == "toggle"),
    BroadcastState.WAITING_FOR_LANGUAGES,
    IsAdmin(),
)
async def broadcast_language_toggle_handler(
    callback: CallbackQuery,
    callback_data: BroadcastLanguageCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    languages: List[str] = data.get("languages", [])
    code = callback_data.language_code
    if code in languages:
        languages.remove(code)
    else:
        languages.append(code)
    await state.update_data(languages=languages)
    await callback.message.edit_reply_markup(
        reply_markup=BroadcastLanguageKeyboard.make(selected=languages),
    )
    await callback.answer()


@router.callback_query(
    BroadcastLanguageCallback.filter(F.action == "done"),
    BroadcastState.WAITING_FOR_LANGUAGES,
    IsAdmin(),
)
async def broadcast_language_done_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    languages: List[str] = data.get("languages", [])
    if not languages:
        await callback.answer(_("Please select at least one."), show_alert=True)
        return
    await state.set_state(BroadcastState.WAITING_FOR_PREMIUM)
    await callback.message.edit_text(
        text=_(
            "<b>Step 2 of 5 — Target audience</b>\n"
            "\n"
            "Choose whether to send to all users or premium users only."
        ),
        reply_markup=BroadcastPremiumKeyboard.make(),
    )
    await callback.answer()


@router.callback_query(
    BroadcastPremiumCallback.filter(),
    BroadcastState.WAITING_FOR_PREMIUM,
    IsAdmin(),
)
async def broadcast_premium_handler(
    callback: CallbackQuery,
    callback_data: BroadcastPremiumCallback,
    state: FSMContext,
) -> None:
    await state.update_data(is_premium=callback_data.is_premium)
    await state.set_state(BroadcastState.WAITING_FOR_CHAT_TYPES)
    await state.update_data(chat_types=[])
    await callback.message.edit_text(
        text=_(
            "<b>Step 3 of 5 — Target chat types</b>\n"
            "\n"
            "Select which types of chats should receive the broadcast.\n"
            "\n"
            "\u2022 <b>Private</b> — direct messages with individual users\n"
            "\u2022 <b>Group</b> — regular group chats\n"
            "\u2022 <b>Supergroup</b> — large supergroup chats\n"
            "\n"
            "Select one or more types, then press <b>Continue</b>."
        ),
        reply_markup=BroadcastChatTypeKeyboard.make(selected=[]),
    )
    await callback.answer()


@router.callback_query(
    BroadcastChatTypeCallback.filter(F.action == "toggle"),
    BroadcastState.WAITING_FOR_CHAT_TYPES,
    IsAdmin(),
)
async def broadcast_chat_type_toggle_handler(
    callback: CallbackQuery,
    callback_data: BroadcastChatTypeCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    chat_types: List[str] = data.get("chat_types", [])
    code = callback_data.chat_type
    if code in chat_types:
        chat_types.remove(code)
    else:
        chat_types.append(code)
    await state.update_data(chat_types=chat_types)
    await callback.message.edit_reply_markup(
        reply_markup=BroadcastChatTypeKeyboard.make(selected=chat_types),
    )
    await callback.answer()


@router.callback_query(
    BroadcastChatTypeCallback.filter(F.action == "done"),
    BroadcastState.WAITING_FOR_CHAT_TYPES,
    IsAdmin(),
)
async def broadcast_chat_type_done_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    chat_types: List[str] = data.get("chat_types", [])
    if not chat_types:
        await callback.answer(_("Please select at least one."), show_alert=True)
        return
    await state.set_state(BroadcastState.WAITING_FOR_DELAY)
    await callback.message.edit_text(
        text=_(
            "<b>Step 4 of 5 — Schedule</b>\n"
            "\n"
            "Choose when the broadcast should begin.\n"
            "\n"
            "You can start immediately or delay the send by a few hours.\n"
            "The bot will wait the selected amount of time before sending the first message.\n"
            "\n"
            "Select a start time below."
        ),
        reply_markup=BroadcastDelayKeyboard.make(),
    )
    await callback.answer()


@router.callback_query(
    BroadcastDelayCallback.filter(F.action == "custom"),
    BroadcastState.WAITING_FOR_DELAY,
    IsAdmin(),
)
async def broadcast_custom_time_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastState.WAITING_FOR_DATETIME)
    example = (datetime.datetime.now(_LOCAL_TZ) + datetime.timedelta(hours=2)).strftime(_DATETIME_FORMAT)
    await callback.message.edit_text(
        text=_(
            "<b>📅 Schedule</b>\n"
            "\n"
            "Send the date and time in this format:\n"
            "<code>DD.MM.YYYY HH:MM</code>  (Tashkent time)\n"
            "\n"
            "Example: <code>%(example)s</code>"
        ) % dict(example=example)
    )
    await callback.answer()


@router.message(BroadcastState.WAITING_FOR_DATETIME, F.text, ~F.text.in_({"⬅️"}), IsAdmin())
async def broadcast_datetime_handler(message: Message, state: FSMContext) -> None:
    try:
        local = datetime.datetime.strptime(message.text.strip(), _DATETIME_FORMAT).replace(tzinfo=_LOCAL_TZ)
    except ValueError:
        await message.answer(
            text=_("❌ Wrong format. Send it like <code>%(example)s</code>.") % dict(
                example=(datetime.datetime.now(_LOCAL_TZ) + datetime.timedelta(hours=2)).strftime(_DATETIME_FORMAT),
            )
        )
        return
    now = datetime.datetime.now(datetime.timezone.utc)
    run_at = local.astimezone(datetime.timezone.utc)
    if run_at <= now + datetime.timedelta(minutes=1):
        await message.answer(text=_("❌ This time has already passed. Send a time in the future."))
        return
    if run_at > now + datetime.timedelta(days=MAX_SCHEDULE_DAYS):
        await message.answer(text=_("❌ You can schedule at most %(days)s days ahead.") % dict(days=MAX_SCHEDULE_DAYS))
        return
    await state.update_data(delay=int((run_at - now).total_seconds()), run_at=run_at.isoformat())
    await state.set_state(BroadcastState.WAITING_FOR_MESSAGE)
    await message.answer(text=_step5_text())


@router.callback_query(
    BroadcastDelayCallback.filter(F.action != "custom"),
    BroadcastState.WAITING_FOR_DELAY,
    IsAdmin(),
)
async def broadcast_delay_handler(
    callback: CallbackQuery,
    callback_data: BroadcastDelayCallback,
    state: FSMContext,
) -> None:
    await state.update_data(delay=callback_data.seconds, run_at=None)
    await state.set_state(BroadcastState.WAITING_FOR_MESSAGE)
    await callback.message.edit_text(text=_step5_text())
    await callback.answer()


@router.message(BroadcastState.WAITING_FOR_MESSAGE, IsAdmin())
async def broadcast_message_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
        reply_markup=message.reply_markup.model_dump(mode="json", exclude_none=True) if message.reply_markup else None,
    )
    await state.set_state(BroadcastState.WAITING_FOR_MODE)
    sent = await message.answer(
        text=_(
            "<b>Send mode</b>\n"
            "\n"
            "Choose how the message should be delivered to recipients.\n"
            "\n"
            "\u2022 <b>Copy</b> \u2014 sends the message as a new message. No \"forwarded from\" label is shown.\n"
            "\u2022 <b>Forward</b> \u2014 forwards the original message. Recipients will see the source sender.\n"
            "\n"
            "Select the desired mode."
        ),
        reply_markup=BroadcastModeKeyboard.make(),
    )
    await state.update_data(inline_message_id=sent.message_id)


@router.callback_query(
    BroadcastModeCallback.filter(),
    BroadcastState.WAITING_FOR_MODE,
    IsAdmin(),
)
async def broadcast_mode_handler(
    callback: CallbackQuery,
    callback_data: BroadcastModeCallback,
    state: FSMContext,
) -> None:
    await state.update_data(mode=callback_data.mode)
    await state.set_state(BroadcastState.WAITING_FOR_CONFIRM)
    data = await state.get_data()
    delay_seconds = data.get("delay", 0)
    delay_label = _delay_label(delay_seconds, data.get("run_at"))
    audience = await BroadcastService.count_audience(
        languages=data.get("languages", []),
        chat_types=data.get("chat_types", []),
        is_premium=data.get("is_premium", False),
    )
    summary = build_broadcast_summary(
        audience=audience,
        mode=_mode_label(callback_data.mode),
        delay_label=delay_label,
    )
    await callback.message.edit_text(
        text=summary,
        reply_markup=BroadcastConfirmKeyboard.make(),
    )
    await callback.answer()


@router.callback_query(
    BroadcastConfirmCallback.filter(F.action == "confirm"),
    BroadcastState.WAITING_FOR_CONFIRM,
    IsAdmin(),
)
async def broadcast_confirm_handler(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    data = await state.get_data()
    await state.clear()
    mode = BroadcastMode(data.get("mode"))
    languages = data.get("languages", [])
    chat_types = data.get("chat_types", [])
    is_premium = data.get("is_premium", False)
    audience = await BroadcastService.count_audience(
        languages=languages,
        chat_types=chat_types,
        is_premium=is_premium,
    )
    delay_seconds = data.get("delay", 0)
    delay_label = _delay_label(delay_seconds, data.get("run_at"))
    started_text = build_broadcast_started(
        audience=audience,
        mode=_mode_label(mode),
        delay_label=delay_label,
    )

    broadcast_id = uuid.uuid4().hex
    await BroadcastService.init_progress(
        broadcast_id=broadcast_id,
        audience=audience,
    )
    await callback.message.edit_text(
        text=started_text,
        reply_markup=BroadcastProgressKeyboard.make(
            broadcast_id=broadcast_id,
            paused=False,
            finished=False,
        ),
    )
    await callback.answer()
    run_date = (
        datetime.datetime.fromisoformat(data["run_at"])
        if data.get("run_at")
        else datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay_seconds)
    )
    scheduler.add_job(
        BroadcastService.create,
        "date",
        id="broadcast:%s" % broadcast_id,
        run_date=run_date,
        misfire_grace_time=None,
        replace_existing=True,
        kwargs=dict(
            source_chat_id=data.get("source_chat_id"),
            source_message_id=data.get("source_message_id"),
            mode=mode,
            broadcast_id=broadcast_id,
            languages=languages,
            chat_types=chat_types,
            is_premium=is_premium,
            reply_markup=data.get("reply_markup"),
            notify_message_id=callback.message.message_id,
            locale=user.language_code if user else None,
        ),
    )


@router.callback_query(
    BroadcastConfirmCallback.filter(F.action == "test"),
    BroadcastState.WAITING_FOR_CONFIRM,
    IsAdmin(),
)
async def broadcast_test_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Send the broadcast only to the admin, exactly as recipients will get it."""
    data = await state.get_data()
    result = await BroadcastService._send(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        source_chat_id=data.get("source_chat_id"),
        source_message_id=data.get("source_message_id"),
        mode=BroadcastMode(data.get("mode")),
        reply_markup=InlineKeyboardMarkup.model_validate(data["reply_markup"]) if data.get("reply_markup") else None,
    )
    await callback.answer(
        text=_("🧪 Test message sent to you. Check it, then confirm or cancel.") if result == "success"
        else _("❌ Could not send the test message."),
        show_alert=True,
    )


@router.callback_query(
    BroadcastConfirmCallback.filter(F.action == "cancel"),
    BroadcastState.WAITING_FOR_CONFIRM,
    IsAdmin(),
)
async def broadcast_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    await callback.message.edit_text(text=_("Broadcast cancelled."))
    await callback.answer()


@router.callback_query(
    BroadcastProgressCallback.filter(F.action == "view"),
    IsAdmin(),
)
async def broadcast_progress_handler(
    callback: CallbackQuery,
    callback_data: BroadcastProgressCallback,
) -> None:
    progress = await BroadcastService.get_progress(
        broadcast_id=callback_data.broadcast_id,
    )
    if not progress:
        await callback.answer(
            text=_("Broadcast not found."),
            show_alert=True,
        )
        return
    status = (
        _("Completed")
        if progress["finished"]
        else _("Stopped")
        if progress["stopped"]
        else _("Paused")
        if progress["paused"]
        else _("In progress")
    )
    alert_text = build_broadcast_progress(progress, status)
    await callback.answer(text=alert_text, show_alert=True)


@router.callback_query(
    BroadcastProgressCallback.filter(F.action.in_({"pause", "resume"})),
    IsAdmin(),
)
async def broadcast_pause_resume_handler(
    callback: CallbackQuery,
    callback_data: BroadcastProgressCallback,
) -> None:
    progress = await BroadcastService.get_progress(broadcast_id=callback_data.broadcast_id)
    if not progress or progress["finished"] or progress["stopped"]:
        await callback.answer(text=_("Broadcast not found."), show_alert=True)
        return
    paused = callback_data.action == "pause"
    await BroadcastService.set_paused(broadcast_id=callback_data.broadcast_id, paused=paused)
    await callback.message.edit_reply_markup(
        reply_markup=BroadcastProgressKeyboard.make(
            broadcast_id=callback_data.broadcast_id,
            paused=paused,
        )
    )
    await callback.answer(
        text=_("Broadcast paused.") if paused else _("Broadcast resumed."),
        show_alert=True,
    )


@router.callback_query(
    BroadcastProgressCallback.filter(F.action == "stop"),
    IsAdmin(),
)
async def broadcast_stop_handler(
    callback: CallbackQuery,
    callback_data: BroadcastProgressCallback,
) -> None:
    progress = await BroadcastService.get_progress(broadcast_id=callback_data.broadcast_id)
    if not progress or progress["finished"]:
        await callback.answer(text=_("Broadcast not found."), show_alert=True)
        return
    await BroadcastService.stop(broadcast_id=callback_data.broadcast_id)
    job = scheduler.get_job("broadcast:%s" % callback_data.broadcast_id)
    if job is not None and job.next_run_time is not None:
        # Not started yet (delayed broadcast): cancel the scheduled run entirely.
        job.remove()
    await callback.message.edit_reply_markup(
        reply_markup=BroadcastProgressKeyboard.make(
            broadcast_id=callback_data.broadcast_id,
            stopped=True,
        )
    )
    await callback.answer(text=_("Broadcast stopped."), show_alert=True)
