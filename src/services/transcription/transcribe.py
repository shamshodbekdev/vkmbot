from typing import BinaryIO, Optional, Union

from schemas.transcription import TranscriptionSchema
from services.transcription_api import TranscriptionAPI


class Transcription:
    @classmethod
    async def transcribe(
        cls,
        file: Union[bytes, BinaryIO],
        filename: str = "audio.mp3",
        language: str = "en",
    ) -> Optional[TranscriptionSchema]:
        # ``filename`` is kept for compatibility; the format is detected by ffmpeg.
        return await TranscriptionAPI.transcribe(file=file, language=language)
