from aiogram.fsm.state import StatesGroup, State


class BroadcastState(StatesGroup):
    WAITING_FOR_LANGUAGES = State(state="waiting_for_broadcast_languages")
    WAITING_FOR_PREMIUM = State(state="waiting_for_broadcast_premium")
    WAITING_FOR_CHAT_TYPES = State(state="waiting_for_broadcast_chat_types")
    WAITING_FOR_DELAY = State(state="waiting_for_broadcast_delay")
    WAITING_FOR_MESSAGE = State(state="waiting_for_broadcast_message")
    WAITING_FOR_MODE = State(state="waiting_for_broadcast_mode")
    WAITING_FOR_CONFIRM = State(state="waiting_for_broadcast_confirm")
