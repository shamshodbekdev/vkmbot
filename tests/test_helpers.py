from schemas.instagram import InstagramResponseSchema
from utils.helpers.instagram import collect_media_items, extract_shortcode


def test_extract_shortcode():
    assert extract_shortcode("https://www.instagram.com/p/aye83DjauH/") == "aye83DjauH"
    assert extract_shortcode("https://www.instagram.com/user/reel/CWqAgUZgCku") == "CWqAgUZgCku"
    assert extract_shortcode("https://www.instagram.com/user/") is None


def test_collect_media_items_keeps_known_kinds_only():
    response = InstagramResponseSchema.model_validate(
        dict(medias=[
            dict(type="video", url="/tmp/a.mp4"),
            dict(type="image", url="/tmp/b.jpg"),
            dict(type="story", url="/tmp/c.bin"),
        ])
    )
    assert collect_media_items(response) == [("/tmp/a.mp4", None, "video"), ("/tmp/b.jpg", None, "photo")]
