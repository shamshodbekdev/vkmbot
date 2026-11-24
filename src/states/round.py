from aiogram.fsm.state import State, StatesGroup


class RoundState(StatesGroup):
    WAITING_VIDEO = State()
