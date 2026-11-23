from aiogram.fsm.state import StatesGroup, State


class MoodState(StatesGroup):
    PLAYLISTS = State()
    TRACKS = State()
