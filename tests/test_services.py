from pathlib import Path

from aiogram.types import FSInputFile, URLInputFile

from schemas.playlist import PlaylistSchema
from services import media_downloader
from services.youtube_api import MAX_AUDIO_SECONDS, _drop_none, _validate, _validate_list
from schemas.youtube_search import SongSchema


def test_drop_none_removes_missing_fields_recursively():
    raw = dict(title="x", description=None, author=dict(name="a", id=None), tracks=[None, dict(videoId="v")])
    assert _drop_none(raw) == dict(title="x", author=dict(name="a"), tracks=[dict(videoId="v")])


def test_validate_tolerates_ytmusicapi_nulls():
    playlist = _validate(PlaylistSchema, dict(id="PL1", title="Top", description=None, year=None))
    assert playlist is not None and playlist.description == ""


def test_validate_list_skips_broken_items():
    songs = _validate_list(SongSchema, [dict(videoId="ok", title="t"), dict(videoId="bad", year="not-a-year")])
    assert [s.videoId for s in songs] == ["ok"]


def test_audio_length_limit_fits_telegram_upload():
    # 128 kbps MP3 of MAX_AUDIO_SECONDS must stay under the upload limit.
    assert MAX_AUDIO_SECONDS * 128_000 / 8 < media_downloader.MAX_UPLOAD_BYTES


def test_as_input_file_picks_local_file_or_url(tmp_path: Path):
    local = tmp_path / "a.mp3"
    local.write_bytes(b"x")
    assert isinstance(media_downloader.as_input_file(str(local)), FSInputFile)
    assert isinstance(media_downloader.as_input_file("https://example.com/a.mp3"), URLInputFile)


def test_discard_only_touches_job_directories(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(media_downloader, "MEDIA_TMP_DIR", tmp_path)
    job = tmp_path / "job1"
    job.mkdir()
    (job / "a.mp4").write_bytes(b"x")
    outside = tmp_path.parent / "keep-me.txt"
    outside.write_text("x")

    media_downloader.discard(str(job / "a.mp4"), str(outside), None, "https://example.com/x")

    assert not job.exists()
    assert outside.exists()
    outside.unlink()
