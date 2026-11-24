# Bots can only download files up to 20 MB from api.telegram.org (getFile);
# a local Bot API server raises that to 2000 MB.
from core.config import config as _config

MAX_FILE_SIZE: int = (2000 if _config.telegram_api_local else 20) * 1024 * 1024
MAX_FILE_SIZE_MB: int = MAX_FILE_SIZE // (1024 * 1024)
MIN_DURATION: int = 2
RECOGNITION_SEARCH_LIMIT: int = 5