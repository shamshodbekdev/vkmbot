import pytest

from utils.validators import extract_instagram_url, extract_tiktok_url, extract_youtube_url


@pytest.mark.parametrize(
    "text, expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
        ("look: youtu.be/dQw4w9WgXcQ !", "https://youtu.be/dQw4w9WgXcQ"),
        ("https://youtube.com/shorts/BGQWPY4IigY?si=abc", "https://youtube.com/shorts/BGQWPY4IigY"),
        ("https://music.youtube.com/watch?v=dQw4w9WgXcQ&list=x", "https://music.youtube.com/watch?v=dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ", "https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ"),
    ],
)
def test_youtube_url_is_extracted(text, expected):
    assert extract_youtube_url(text) == expected


@pytest.mark.parametrize("text", ["shape of you", "https://www.youtube.com/@channel", "https://example.com/watch?v=dQw4w9WgXcQ"])
def test_youtube_url_rejects_non_videos(text):
    assert extract_youtube_url(text) is None


def test_tiktok_url():
    url = "https://www.tiktok.com/@scout2015/video/6718335390845095173"
    assert extract_tiktok_url("watch " + url) == url
    assert extract_tiktok_url("https://vm.tiktok.com/ZMabc123/")
    assert extract_tiktok_url("no link here") is None


def test_instagram_url():
    assert extract_instagram_url("https://www.instagram.com/reel/CWqAgUZgCku/") == "https://www.instagram.com/reel/CWqAgUZgCku"
    assert extract_instagram_url("https://instagram.com/p/aye83DjauH") == "https://instagram.com/p/aye83DjauH"
    assert extract_instagram_url("https://instagram.com/someone") is None
