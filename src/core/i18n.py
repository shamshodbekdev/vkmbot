import logging
from pathlib import Path
from typing import Optional

from aiogram.utils.i18n import I18n
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

from core.config import LOCALES_DIR

DOMAIN: str = "messages"
DEFAULT_LOCALE: str = "en"

logger = logging.getLogger(__name__)


def compile_locales(path: Path = LOCALES_DIR, domain: str = DOMAIN) -> None:
    """Compile every <locale>/LC_MESSAGES/<domain>.po into .mo when missing or outdated.

    Compiled catalogs are git-ignored, so this keeps a fresh checkout runnable and
    guarantees the bot always serves the latest translations.
    """
    for po_path in sorted(path.glob("*/LC_MESSAGES/%s.po" % domain)):
        mo_path = po_path.with_suffix(".mo")
        if mo_path.exists() and mo_path.stat().st_mtime >= po_path.stat().st_mtime:
            continue
        with po_path.open("rb") as po_file:
            # No locale is passed on purpose: custom codes such as "uzc" are not Babel locales.
            catalog = read_po(po_file)
        with mo_path.open("wb") as mo_file:
            write_mo(mo_file, catalog)
        logger.info("Compiled translations: %s", mo_path)


_i18n: Optional[I18n] = None


def get_i18n() -> I18n:
    """Shared I18n instance (compiled on first use).

    Handlers get translations from I18nMiddleware. Code that runs outside an update,
    such as scheduler jobs, must open a context explicitly::

        with get_i18n().context(), get_i18n().use_locale("ru"):
            text = _("...")
    """
    global _i18n
    if _i18n is None:
        compile_locales()
        _i18n = I18n(path=LOCALES_DIR, default_locale=DEFAULT_LOCALE, domain=DOMAIN)
    return _i18n
