import asyncio

import pytest

from keyboard.inline.audio_download import AudioDownloadKeyboard
from services import media_downloader
from services.audio_effects import EFFECTS
from services.social_api import open_graph
from utils.validators import extract_social_url


@pytest.mark.parametrize(
    "text, platform",
    [
        ("https://www.pinterest.com/pin/664281013778109217/", "pinterest"),
        ("https://ru.pinterest.com/pin/1084663891475263837", "pinterest"),
        ("see https://pin.it/3xYzAbC", "pinterest"),
        ("https://www.snapchat.com/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYYWtidGhudGZp", "snapchat"),
        ("https://www.snapchat.com/@snapchat/spotlight/W7_EDlXWTBiXAEEni", "snapchat"),
        ("https://t.snapchat.com/AbCdEf12", "snapchat"),
        ("https://likee.video/@user_1/video/7093167848050058862", "likee"),
        ("https://l.likee.video/v/k6QcOp", "likee"),
    ],
)
def test_social_links_are_detected(text, platform):
    found = extract_social_url(text)
    assert found and found[0] == platform and found[1].startswith("https://")


@pytest.mark.parametrize("text", ["hello", "https://www.pinterest.com/someone/", "https://snapchat.com/add/user"])
def test_non_media_links_are_ignored(text):
    assert extract_social_url(text) is None


def test_open_graph_parser_handles_any_attribute_order():
    page = (
        '<meta content="https://i.pinimg.com/736x/aa/bb.jpg" name="og:image" property="og:image"/>'
        '<meta property="og:video:secure_url" content="https://cdn.example/v.mp4?a=1&amp;b=2">'
    )
    og = open_graph(page)
    assert og["og:image"] == "https://i.pinimg.com/736x/aa/bb.jpg"
    assert og["og:video:secure_url"] == "https://cdn.example/v.mp4?a=1&b=2"


@pytest.mark.parametrize(
    "message, retry",
    [
        ("ERROR: [youtube] x: Sign in to confirm you’re not a bot.", True),
        ("HTTP Error 429: Too Many Requests", True),
        ("HTTP Error 503: Service Unavailable", True),
        ("Read timed out", True),
        ("ERROR: [youtube] x: Video unavailable", False),
        ("ERROR: Requested format is not available", False),
    ],
)
def test_only_transient_errors_are_retried(message, retry):
    assert media_downloader.is_retryable(message) is retry


def test_user_download_slots_are_limited_and_released():
    async def scenario():
        limit = media_downloader.MAX_DOWNLOADS_PER_USER
        contexts = [media_downloader.user_download_slot(42) for _ in range(limit + 1)]
        results = [await c.__aenter__() for c in contexts]
        assert results == [True] * limit + [False]
        for c in reversed(contexts):
            await c.__aexit__(None, None, None)
        async with media_downloader.user_download_slot(42) as again:
            assert again is True
        async with media_downloader.user_download_slot(43) as other_user:
            assert other_user is True

    asyncio.run(scenario())
    assert 42 not in media_downloader._user_active


def test_audio_keyboard_layout():
    def rows(markup):
        return [[b.text for b in row] for row in markup.inline_keyboard]

    assert rows(AudioDownloadKeyboard.make("dQw4w9WgXcQ", like_buttons=True)) == [
        ["❤️", "💾"],
        ["🔗 Add to group"],
        ["🎧 8D", "🏛 Concert", "🐢 Slowed"],
    ]
    assert rows(AudioDownloadKeyboard.make("dQw4w9WgXcQ", like_buttons=True, liked=True))[0] == ["💔", "💾"]
    assert rows(AudioDownloadKeyboard.make("dQw4w9WgXcQ", like_buttons=False))[0] == ["💾"]


def test_like_button_toggles_between_like_and_unlike():
    from filters.callback.audio_playlist import AudioPlaylistCallback

    def first(markup):
        return AudioPlaylistCallback.unpack(markup.inline_keyboard[0][0].callback_data).action

    assert first(AudioDownloadKeyboard.make("dQw4w9WgXcQ")) == "like"
    assert first(AudioDownloadKeyboard.make("dQw4w9WgXcQ", liked=True)) == "unlike"


def test_add_to_group_button_uses_real_bot_username(monkeypatch):
    from core import bot_identity

    monkeypatch.setattr(bot_identity, "_username", "QoriqchiUzBbot")
    url = AudioDownloadKeyboard.make("dQw4w9WgXcQ").inline_keyboard[1][0].url
    assert url == "https://t.me/QoriqchiUzBbot?startgroup=true"


def test_every_effect_button_has_an_implementation():
    markup = AudioDownloadKeyboard.make("dQw4w9WgXcQ")
    effect_keys = {b.callback_data.split(":")[1] for row in markup.inline_keyboard for b in row if (b.callback_data or "").startswith("fx:")}
    assert effect_keys == set(EFFECTS)


def test_jpeg_thumbnails_are_ranked_best_first_and_skip_webp():
    from services.youtube_api import jpeg_thumbnails

    base = "https://i.ytimg.com/vi/abc"
    info = dict(id="abc", thumbnails=[
        dict(url=base + "/hqdefault.jpg?sqp=x", width=336, height=188),
        dict(url=base + "/maxresdefault.jpg"),
        dict(url="https://i.ytimg.com/vi_webp/abc/maxresdefault.webp"),
        dict(url=base + "/sddefault.jpg"),
        dict(url=base + "/hqdefault.jpg", width=480, height=360),
    ])
    urls = jpeg_thumbnails(info)
    assert urls[0] == base + "/maxresdefault.jpg"
    assert urls[1] == base + "/sddefault.jpg"
    assert all(".webp" not in u for u in urls)
    assert base + "/hqdefault.jpg" in urls  # guaranteed fallback is always present
    assert urls.index(base + "/hqdefault.jpg") < urls.index(base + "/hqdefault.jpg?sqp=x")  # bigger first


def test_youtube_link_keyboard_has_video_and_audio():
    from filters.callback.youtube_link import YoutubeLinkCallback
    from keyboard.inline.youtube_link import YoutubeLinkKeyboard

    buttons = [b for row in YoutubeLinkKeyboard.make("dQw4w9WgXcQ").inline_keyboard for b in row]
    assert [b.text for b in buttons] == ["📼 Video", "🎧 Audio"]
    assert [YoutubeLinkCallback.unpack(b.callback_data).kind for b in buttons] == ["video", "audio"]
