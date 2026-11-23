"""Free, local speech-to-text with faster-whisper (used to find a song by its lyrics).

The model runs on this server's CPU. It is loaded on first use (~0.6 GB RAM for
"small") and requests are processed one at a time so the bot's other work keeps
enough CPU.
"""
import asyncio
import logging
import tempfile
import threading
from typing import BinaryIO, Optional, Union

from schemas.transcription import TranscriptionSchema, TranscriptionWordSchema
from services.media_downloader import MEDIA_TMP_DIR
from services.shazam_api import to_wav

logger = logging.getLogger(__name__)

WHISPER_MODEL: str = "small"
WHISPER_THREADS: int = 2
MAX_AUDIO_SECONDS: int = 120

_model = None
_model_lock = threading.Lock()
_queue = asyncio.Semaphore(1)


def _load_model():
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel

            logger.info("Loading Whisper model %r...", WHISPER_MODEL)
            _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8", cpu_threads=WHISPER_THREADS)
    return _model


def _transcribe(wav: bytes, language: str) -> TranscriptionSchema:
    model = _load_model()
    MEDIA_TMP_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=MEDIA_TMP_DIR) as tmp:
        tmp.write(wav)
        tmp.flush()
        segments, info = model.transcribe(tmp.name, language=language, word_timestamps=True, vad_filter=True)
        segments = list(segments)
    words = [
        TranscriptionWordSchema(word=w.word, start=w.start, end=w.end)
        for s in segments for w in (s.words or [])
    ]
    return TranscriptionSchema(
        text=" ".join(s.text.strip() for s in segments).strip(),
        task="transcribe",
        language=info.language,
        duration=info.duration,
        words=words,
    )


class TranscriptionAPI:
    @classmethod
    async def transcribe(cls, file: Union[bytes, BinaryIO], language: str = "en") -> Optional[TranscriptionSchema]:
        try:
            data = file if isinstance(file, (bytes, bytearray)) else file.read()
            wav = await to_wav(bytes(data), MAX_AUDIO_SECONDS)
            if not wav:
                return None
            async with _queue:
                return await asyncio.to_thread(_transcribe, wav, language)
        except Exception as error:
            logger.warning("Transcription failed: %r", error)
            return None
