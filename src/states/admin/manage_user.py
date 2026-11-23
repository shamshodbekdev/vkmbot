from aiogram.fsm.state import StatesGroup, State

class ManageUserState(StatesGroup):
    WAITING_FOR_CHAT_ID = State(state="user_waiting_for_chat_id")
