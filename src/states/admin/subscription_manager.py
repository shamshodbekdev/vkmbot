from aiogram.fsm.state import StatesGroup, State


class SubscriptionState(StatesGroup):
    WAITING_FOR_CHAT = State(state="sub_waiting_for_chat")
    WAITING_FOR_INVITE_LINK = State(state="sub_waiting_for_invite_link")
    WAITING_FOR_MAX_AUDIENCE = State(state="sub_waiting_for_max_audience")
