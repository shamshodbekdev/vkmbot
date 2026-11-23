from aiogram.fsm.state import StatesGroup, State

class ManageAdminState(StatesGroup):
    WAITING_FOR_CHAT_ID = State(state="waiting_for_chat_id")