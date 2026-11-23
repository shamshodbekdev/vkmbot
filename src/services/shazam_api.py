"""Free, local song recognition with ShazamIO.

Input can be any audio/video Telegram gives us (OGG/Opus voice notes, MP4 video
notes, MP3/M4A files...). It is normalised with ffmpeg to 16 kHz mono WAV first,
so recognition does not depend on which codecs ShazamIO's decoder supports.
"""
import logging
import tempfile
from pathlib import Path
from typing import BinaryIO, Optional, Union

from shazamio import Shazam as ShazamClient

from schemas.shazam import ShazamSchema
from services.media_downloader import MEDIA_TMP_DIR, run_ffmpeg

logger = logging.getLogger(__name__)

# Shazam only needs a short sample; cap the decoded audio to keep ffmpeg fast.
MAX_SAMPLE_SECONDS: int = 60

_client: Optional[ShazamClient] = None


def _shazam() -> ShazamClient:
    global _client
    if _client is None:
        _client = ShazamClient()
    return _client


async def to_wav(data: bytes, seconds: Optional[int] = None) -> Optional[bytes]:
    """Decode any audio/video to 16 kHz mono WAV.

    Written to a real file, not a pipe: on a pipe ffmpeg cannot go back and fill
    in the WAV header's length fields, and ShazamIO rejects such files.
    """
    MEDIA_TMP_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=MEDIA_TMP_DIR) as tmp:
        args = ["-y", "-i", "pipe:0", "-vn", "-ac", "1", "-ar", "16000"]
        if seconds:
            args += ["-t", str(seconds)]
        if await run_ffmpeg(*args, tmp.name, stdin=data) is None:
            return None
        return Path(tmp.name).read_bytes() or None


class ShazamAPI:
    @classmethod
    async def recognize(cls, file: Union[bytes, BinaryIO]) -> Optional[ShazamSchema]:
        try:
            data = file if isinstance(file, (bytes, bytearray)) else file.read()
            wav = await to_wav(bytes(data), MAX_SAMPLE_SECONDS)
            if not wav:
                return None
            raw = await _shazam().recognize(wav)
            return ShazamSchema.model_validate(raw or {})
        except Exception as error:
            logger.warning("Shazam recognition failed: %r", error)
            return None
