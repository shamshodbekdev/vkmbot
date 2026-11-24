import logging
from typing import List, Optional, Union

from aiogram import F, Router
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message, URLInputFile
from aiogram.utils.i18n import gettext as _

from core.config import config
from database.models import InstagramMedia
from filters.common import InstagramUrlFilter
from keyboard.inline import VideoRecognizeKeyboard
from services.instagram import InstagramConvert
from services.media_downloader import (
    VIDEO_CACHE_VALID_FROM,
    FileTooLargeError,
    as_input_file,
    discard,
    remember_video_source,
    video_meta,
)
from utils.constants import MEDIA_GROUP_CHUNK
from utils.helpers import collect_media_items, extract_shortcode, safe_delete
from utils.helpers.media_errors import file_too_large_text

router = Router()
logger = logging.getLogger(__name__)

MEDIA_UPLOAD_TIMEOUT: int = 300
InputMedia = Union[InputMediaPhoto, InputMediaVideo]


def _caption() -> str:
    return _("Find any music you want quickly and easily via %(username_bot)s!") % dict(
        username_bot=config.telegram_username,
    )


def _input_media(kind: str, media: Union[str, URLInputFile], caption: Optional[str], thumb: Optional[str] = None,
                 meta: Optional[dict] = None) -> InputMedia:
    if kind == "video":
        return InputMediaVideo(
            media=media,
            thumbnail=URLInputFile(thumb) if thumb else None,
            supports_streaming=True,
            caption=caption,
            **(meta or {}),
        )
    return InputMediaPhoto(media=media, caption=caption)


async def _send_cached(message: Message, cached: List[InstagramMedia], url: str = "") -> None:
    if len(cached) == 1:
        item = cached[0]
        if item.kind == "video":
            sent = await message.answer_video(
                video=item.file_id,
                caption=_caption(),
                reply_markup=VideoRecognizeKeyboard.make(),
            )
            await remember_video_source(sent, url)
        else:
            await message.answer_photo(photo=item.file_id, caption=_caption())
        return

    for start in range(0, len(cached), MEDIA_GROUP_CHUNK):
        chunk = cached[start:start + MEDIA_GROUP_CHUNK]
        await message.answer_media_group(
            media=[
                _input_media(item.kind, item.file_id, _caption() if index == 0 else None)
                for index, item in enumerate(chunk)
            ]
        )


async def _remember(shortcode: Optional[str], index: int, kind: str, sent: Message, url: str = "") -> None:
    await remember_video_source(sent, url)
    if not shortcode:
        return
    if kind == "video" and sent.video:
        file_id = sent.video.file_id
    elif kind == "photo" and sent.photo:
        file_id = sent.photo[-1].file_id
    else:
        return
    # Replaces a stale (pre-fix, square) cache row for this item, if any.
    await InstagramMedia.filter(shortcode=shortcode, index_number=index).delete()
    await InstagramMedia.create(shortcode=shortcode, index_number=index, kind=kind, file_id=file_id)


@router.message(F.text, InstagramUrlFilter())
async def instagram_handler(message: Message, instagram_url: str) -> None:
    processing = await message.answer(text=_("Processing..."))
    items: List[tuple] = []
    try:
        shortcode = extract_shortcode(instagram_url)
        if shortcode:
            cached = await InstagramMedia.filter(shortcode=shortcode).order_by("index_number")
            # Videos cached before the size fix would show as squares: download them again.
            if cached and all(item.kind != "video" or item.created_at >= VIDEO_CACHE_VALID_FROM for item in cached):
                await _send_cached(message, cached, instagram_url)
                return

        response = await InstagramConvert.convert(url=instagram_url)
        if not response:
            await message.answer(text=_("Could not fetch the Instagram media."))
            return

        items = collect_media_items(response)
        if not items:
            await message.answer(text=_("No downloadable video found."))
            return

        if len(items) == 1:
            url, thumb, kind = items[0]
            if kind == "video":
                sent = await message.answer_video(
                    video=as_input_file(url, timeout=MEDIA_UPLOAD_TIMEOUT),
                    thumbnail=URLInputFile(thumb) if thumb else None,
                    supports_streaming=True,
                    **await video_meta(url),
                    caption=_caption(),
                    reply_markup=VideoRecognizeKeyboard.make(),
                )
            else:
                sent = await message.answer_photo(
                    photo=as_input_file(url, timeout=MEDIA_UPLOAD_TIMEOUT),
                    caption=_caption(),
                )
            await _remember(shortcode, 0, kind, sent, instagram_url)
            return

        for start in range(0, len(items), MEDIA_GROUP_CHUNK):
            chunk = items[start:start + MEDIA_GROUP_CHUNK]
            metas = [await video_meta(url) if kind == "video" else {} for url, _thumb, kind in chunk]
            sent_messages = await message.answer_media_group(
                media=[
                    _input_media(
                        kind,
                        as_input_file(url, timeout=MEDIA_UPLOAD_TIMEOUT),
                        _caption() if index == 0 else None,
                        thumb,
                        metas[index],
                    )
                    for index, (url, thumb, kind) in enumerate(chunk)
                ]
            )
            for offset, (sent, (_url, _thumb, kind)) in enumerate(zip(sent_messages, chunk)):
                await _remember(shortcode, start + offset, kind, sent, instagram_url)
    except FileTooLargeError:
        await message.answer(text=file_too_large_text())
    except Exception:
        logger.exception("Instagram download failed for %s", instagram_url)
        await message.answer(text=_("Could not fetch the Instagram media."))
    finally:
        discard(*(url for url, _thumb, _kind in items))
        await safe_delete(processing)
