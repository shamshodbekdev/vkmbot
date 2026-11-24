import pytest

from filters.callback.new_songs import NewSongsCallback
from keyboard.inline.new_songs import NewSongsKeyboard
from schemas.playlist import PlaylistArtistSchema, PlaylistTrackSchema
from schemas.youtube_search import SongSchema
from services.youtube.new_songs import clean_title, track_label


@pytest.mark.parametrize("raw, clean", [
    ("Bul Beni (Official Video)", "Bul Beni"),
    ("Dai Dai [Official Music Video]", "Dai Dai"),
    ("Guzarish | Official Audio", "Guzarish"),
    ("Song (Lyric Video)", "Song"),
    ("Плохая (Премьера клипа 2026)", "Плохая"),
    ("Live Forever (Remastered)", "Live Forever (Remastered)"),  # not noise: kept
])
def test_clean_title(raw, clean):
    assert clean_title(raw) == clean


def test_track_label_does_not_repeat_the_artist():
    a = PlaylistTrackSchema(videoId="x", title="Bul Beni (Official Video)", artists=[PlaylistArtistSchema(name="Emre Aydın")])
    b = PlaylistTrackSchema(videoId="y", title="Emre Aydın - Bul Beni", artists=[PlaylistArtistSchema(name="Emre Aydın")])
    assert track_label(a) == "Emre Aydın — Bul Beni"
    assert track_label(b) == "Emre Aydın - Bul Beni"


def _tracks(n):
    return [PlaylistTrackSchema(videoId="v%010d" % i, title="Song %d" % i, artists=[PlaylistArtistSchema(name="A")]) for i in range(n)]


def test_page_keyboard_navigation():
    first = NewSongsKeyboard.page(_tracks(10), page=0, has_next=True).inline_keyboard
    assert len(first) == 11 and [b.text for b in first[-1]] == ["➡️"]
    middle = NewSongsKeyboard.page(_tracks(10), page=3, has_next=True).inline_keyboard
    assert [b.text for b in middle[-1]] == ["⬅️", "➡️"]
    last = NewSongsKeyboard.page(_tracks(4), page=9, has_next=False).inline_keyboard
    assert [b.text for b in last[-1]] == ["⬅️"]
    assert all(len(b.callback_data.encode()) <= 64 for row in first for b in row)


def test_versions_keyboard():
    songs = [SongSchema(videoId="s%010d" % i, title="t") for i in range(5)]
    rows = NewSongsKeyboard.versions("vid12345678", songs, page=2).inline_keyboard
    assert rows[0][0].text == "🎬 Video"
    assert [b.text for b in rows[1]] == ["1", "2", "3", "4", "5"]
    assert rows[-1][0].text == "⬅️ NEW Popular Songs"
    assert NewSongsCallback.unpack(rows[-1][0].callback_data).page == 2


@pytest.mark.parametrize("channel, title, label", [
    ("Rammstein Official", "Rammstein - Live in Mexico City - Du Hast", "Rammstein - Live in Mexico City - Du Hast"),
    ("Helene Fischer (Official)", "Atemlos", "Helene Fischer — Atemlos"),
    ("AdeleVEVO", "Hello", "Adele — Hello"),
    ("Munisa Rizayeva - Topic", "Adolar Etma", "Munisa Rizayeva — Adolar Etma"),
])
def test_channel_suffixes_are_removed_from_artist(channel, title, label):
    track = PlaylistTrackSchema(videoId="x", title=title, artists=[PlaylistArtistSchema(name=channel)])
    assert track_label(track) == label
