from typing import BinaryIO, Optional, Union

from schemas.shazam import ShazamSchema
from services.shazam_api import ShazamAPI


class Shazam:
    @classmethod
    async def recognize(cls, file: Union[bytes, BinaryIO], filename: str = "audio.mp3") -> Optional[ShazamSchema]:
        # ``filename`` is kept for compatibility; the format is detected by ffmpeg.
        return await ShazamAPI.recognize(file=file)
