from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TikTokMusicInfoSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[int] = None


class TikTokAuthorSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    unique_id: Optional[str] = None
    nickname: Optional[str] = None


class TikTokSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    title: Optional[str] = None
    cover: Optional[str] = None
    duration: Optional[int] = None
    play: Optional[str] = None
    size: Optional[int] = None
    play_count: Optional[int] = None
    digg_count: Optional[int] = None
    music_info: Optional[TikTokMusicInfoSchema] = None
    author: Optional[TikTokAuthorSchema] = None
