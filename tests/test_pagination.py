from filters.callback.youtube_search import YoutubeSearchCallback
from keyboard.inline.youtube_search import YoutubeSearchKeyboard
from schemas.youtube_search import SongSchema


def _nav_targets(markup):
    """Pages that the navigation buttons point to."""
    pages = []
    for row in markup.inline_keyboard:
        for button in row:
            data = button.callback_data or ""
            if data.startswith(YoutubeSearchCallback.__prefix__ + ":"):
                pages.append(YoutubeSearchCallback.unpack(data).page)
    return pages


def _songs(n):
    return [SongSchema(videoId="v%02d" % i, title="t%d" % i) for i in range(n)]


def test_first_page_previous_button_only_shows_a_notice():
    from filters.callback.first_page import FirstPageCallback

    markup = YoutubeSearchKeyboard.make(_songs(10), query="q", page=0, limit=10, has_next=True, has_next_next=True)
    assert [b.text for b in markup.inline_keyboard[-1]] == ["⬅️", "❌", "➡️"]
    assert markup.inline_keyboard[-1][0].callback_data == FirstPageCallback().pack()
    assert _nav_targets(markup) == [1]  # only ➡️ changes the page


def test_last_page_has_no_next_button():
    markup = YoutubeSearchKeyboard.make(_songs(4), query="q", page=3, limit=10, has_next=False)
    assert _nav_targets(markup) == [2]


def test_layout_is_two_rows_of_five_then_prev_close_next():
    markup = YoutubeSearchKeyboard.make(_songs(10), query="q", page=1, limit=10, has_next=True, has_next_next=True)
    rows = [[b.text for b in row] for row in markup.inline_keyboard]
    assert rows == [
        ["11", "12", "13", "14", "15"],
        ["16", "17", "18", "19", "20"],
        ["⬅️", "❌", "➡️"],
    ]


def test_no_bulk_download_or_double_jump_buttons():
    markup = YoutubeSearchKeyboard.make(_songs(10), query="q", page=2, limit=10, has_next=True, has_next_next=True)
    texts = [b.text for row in markup.inline_keyboard for b in row]
    assert "⬇️" not in texts and not any("2X" in t for t in texts)


def test_single_page_has_notice_and_close_only():
    markup = YoutubeSearchKeyboard.make(_songs(3), query="q", page=0, limit=10, has_next=False)
    assert _nav_targets(markup) == []
    assert [b.text for b in markup.inline_keyboard[-1]] == ["⬅️", "❌"]


def test_numbers_continue_across_pages():
    markup = YoutubeSearchKeyboard.make(_songs(10), query="q", page=2, limit=10, has_next=True)
    numbers = [b.text for row in markup.inline_keyboard for b in row if b.text.isdigit()]
    assert numbers[0] == "21" and numbers[-1] == "30"


def test_callback_data_fits_telegram_limit():
    # The query is stored in Redis and only a 16-char token travels in callback_data.
    data = YoutubeSearchCallback(query="0123456789abcdef", page=99, limit=10).pack()
    assert len(data.encode()) <= 64
