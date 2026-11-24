from typing import Dict, Tuple

LANGUAGES: Tuple[Tuple[str, str, str], ...] = (
    ("uz", "🇺🇿 O'zbekcha", "🇺🇿 O'zbekcha ✅"),
    ("uzc", "🇺🇿 Ўзбекча", "🇺🇿 Ўзбекча ✅"),
    ("ru", "🇷🇺 Русский", "🇷🇺 Русский ✅"),
    ("en", "🇺🇸 English", "🇺🇸 English ✅"),
)

# Shown before the user has a language, so it is written in all of them at once.
LANGUAGE_PROMPT: str = (
    "O'zingizga qulay tilni tanlang\n"
    "Выбери язык, который тебе нравится\n"
    "Choose the language you like"
)

# Statistics group both Uzbek scripts (Latin "uz" and Cyrillic "uzc") under "uz".
LANGUAGE_GROUPS: Dict[str, Tuple[str, ...]] = {
    "uz": ("uz", "uzc"),
}
