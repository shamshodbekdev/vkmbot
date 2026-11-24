"""Audio effects (8D, Concert Hall, Slowed + reverb) rendered locally with ffmpeg."""
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from services.media_downloader import fits_upload_limit, new_job_dir, run_ffmpeg

logger = logging.getLogger(__name__)

OUTPUT_BITRATE: str = "192k"


@dataclass(frozen=True)
class AudioEffect:
    key: str
    suffix: str
    filters: str


EFFECTS: Dict[str, AudioEffect] = {
    # A slow left <-> right pulsation makes the sound "circle" around the listener.
    "8d": AudioEffect("8d", "8D", "aresample=44100,apulsator=hz=0.125:amount=0.9:width=1,aecho=0.8:0.88:30:0.25"),
    # Several decaying early reflections + wider stereo image = a large hall.
    "concert": AudioEffect(
        "concert",
        "Concert Hall",
        "aresample=44100,aecho=0.8:0.88:60|120|180|240:0.4|0.3|0.2|0.12,extrastereo=m=1.3",
    ),
    # 0.85x speed and pitch (classic "slowed + reverb").
    "slowed": AudioEffect("slowed", "Slowed", "aresample=44100,asetrate=37485,aresample=44100,aecho=0.8:0.88:80:0.25"),
}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


async def apply_effect(source: Path, effect_key: str) -> Optional[Path]:
    """Render ``source`` with the effect into a new MP3 in its own job directory."""
    effect = EFFECTS.get(effect_key)
    if effect is None:
        logger.warning("Unknown audio effect %r", effect_key)
        return None
    if not ffmpeg_available():
        logger.error("ffmpeg is not installed: audio effects are unavailable")
        return None
    output = new_job_dir() / ("%s.mp3" % effect.key)
    result = await run_ffmpeg(
        "-y", "-i", str(source), "-vn", "-ac", "2", "-af", effect.filters,
        "-c:a", "libmp3lame", "-b:a", OUTPUT_BITRATE, str(output),
    )
    if result is None or not output.is_file() or not fits_upload_limit(output):
        return None
    return output
