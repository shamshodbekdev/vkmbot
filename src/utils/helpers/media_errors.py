from aiogram.utils.i18n import gettext as _

from services.media_downloader import MAX_UPLOAD_MB


def file_too_large_text() -> str:
    """Shown when even the smallest version of a video is above Telegram's upload limit."""
    return _("❌ The file is too large (over %(limit)sMB). Please choose another video.") % dict(limit=MAX_UPLOAD_MB)
