from aiogram.fsm.state import StatesGroup, State


class TranscriptionState(StatesGroup):
    WAITING_FOR_LANGUAGE = State(state="waiting_for_transcription_language")
