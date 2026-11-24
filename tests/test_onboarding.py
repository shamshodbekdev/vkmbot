from types import SimpleNamespace

from keyboard.inline.language import LanguageKeyboard
from keyboard.inline.subscription_check import SubscriptionCheckKeyboard
from utils.constants import LANGUAGE_PROMPT
from utils.constants.subscription import CHECK_SUBSCRIPTIONS_CALLBACK


def test_first_visit_language_keyboard_has_four_languages_and_no_close():
    markup = LanguageKeyboard.make(action="start", closable=False)
    labels = [b.text for row in markup.inline_keyboard for b in row]
    assert labels == ["🇺🇿 O'zbekcha", "🇺🇿 Ўзбекча", "🇷🇺 Русский", "🇺🇸 English"]
    assert all(":start" in b.callback_data for row in markup.inline_keyboard for b in row)


def test_settings_language_keyboard_keeps_close_button():
    labels = [b.text for row in LanguageKeyboard.make("ru").inline_keyboard for b in row]
    assert "🇷🇺 Русский ✅" in labels and "Close" in labels


def test_language_prompt_is_trilingual():
    assert LANGUAGE_PROMPT.split("\n") == [
        "O'zingizga qulay tilni tanlang",
        "Выбери язык, который тебе нравится",
        "Choose the language you like",
    ]


def test_subscription_keyboard_subscribe_per_channel_then_confirm():
    subs = [SimpleNamespace(invite_link="https://t.me/+a"), SimpleNamespace(invite_link=None), SimpleNamespace(invite_link="https://t.me/+b")]
    buttons = [(b.text, b.url or b.callback_data) for row in SubscriptionCheckKeyboard.make(subs, CHECK_SUBSCRIPTIONS_CALLBACK).inline_keyboard for b in row]
    assert buttons == [("➕ Subscribe", "https://t.me/+a"), ("➕ Subscribe", "https://t.me/+b"), ("✅ Confirm", CHECK_SUBSCRIPTIONS_CALLBACK)]
