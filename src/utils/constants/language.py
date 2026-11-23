from typing import Dict, Tuple

LANGUAGES: Tuple[Tuple[str, str, str], ...] = (
    ("uz", "🇺🇿 O‘zbekcha", "🇺🇿 O‘zbekcha ✅"),
    ("uzc", "🇺🇿 Ўзбекча", "🇺🇿 Ўзбекча ✅"),
    ("en", "🇬🇧 English", "🇬🇧 English ✅"),
    ("ru", "🇷🇺 Russian", "🇷🇺 Russian ✅"),
)

# Statistics group both Uzbek scripts (Latin "uz" and Cyrillic "uzc") under "uz".
LANGUAGE_GROUPS: Dict[str, Tuple[str, ...]] = {
    "uz": ("uz", "uzc"),
}
