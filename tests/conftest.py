import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Dummy settings so modules that import core.config can be loaded without a real .env.
os.environ.setdefault("TELEGRAM_TOKEN", "123456:test-token")
os.environ.setdefault("TELEGRAM_USERNAME", "@test_bot")
os.environ.setdefault("TELEGRAM_ID", "1")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgres://user:password@localhost:5432/test")


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def i18n_context():
    """Activate the project's translations (English), as I18nMiddleware does for real updates."""
    from core.i18n import get_i18n

    i18n = get_i18n()
    with i18n.context(), i18n.use_locale("en"):
        yield i18n
