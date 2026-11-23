from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class SongArtistSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    id: Optional[str] = None


class SongAlbumSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    id: Optional[str] = None


class SongThumbnailSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str = ""
    width: int = 0
    height: int = 0


class SongSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    videoId: str = ""
    title: str = ""
    artists: List[SongArtistSchema] = []
    thumbnails: List[SongThumbnailSchema] = []
    duration: Optional[str] = None
    category: Optional[str] = None
    album: Optional[SongAlbumSchema] = None
    duration: Optional[str] = None
    year: Optional[int] = None
    duration_seconds: Optional[int] = None
    views: Optional[str] = None
    is_explicit: Optional[bool] = None
